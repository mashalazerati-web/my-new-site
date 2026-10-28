# ai_module/services/context_builder.py
"""
Context Builder — تبدیل داده‌های دیتابیس به ScheduleContext
"""

import jdatetime
from typing import Optional, Dict, List

from django.db.models import Q

from api.models import (
    Ward, Profile, ShiftRequest, FinalSchedule, DraftSchedule,
    ShiftCode, Holiday,
)
from ai_module.models import SpecialScheduleConfig

from ai_module.rules import ScheduleContext, StaffInfo


class ContextBuilderError(Exception):
    """خطای Context Builder"""
    pass


class ContextBuilder:
    """بیلدر Context"""

    # ============================================================
    # Helper Methods
    # ============================================================

    @staticmethod
    def _get_days_in_month(year: int, month: int) -> int:
        days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
        return days_in_month[month - 1]

    @staticmethod
    def _get_weekend_days(year: int, month: int, days_in_month: int) -> set:
        weekend_days = set()
        for day in range(1, days_in_month + 1):
            try:
                jalali = jdatetime.date(year, month, day)
                if jalali.weekday() == 6:
                    weekend_days.add(day)
            except Exception:
                pass
        return weekend_days

    @staticmethod
    def _get_holidays(year: int, month: int) -> set:
        month_prefix = f"{year}-{str(month).zfill(2)}"
        holidays = Holiday.objects.filter(
            date__startswith=month_prefix
        ).values_list('date', flat=True)

        holiday_days = set()
        for h in holidays:
            try:
                day = int(h.split('-')[2])
                holiday_days.add(day)
            except (IndexError, ValueError):
                continue

        return holiday_days

    # ============================================================
    # ✅ فیلتر staff بر اساس schedule_type
    # ============================================================
    @staticmethod
    def _get_staff(ward, year=None, month=None, schedule_type='main') -> List[Profile]:
        """
        دریافت پرسنل با اعمال:
        - فیلتر دسته پرسنل بر اساس schedule_type
        - حذف‌های موقت سرپرستار
        """
        from api.models import ScheduleStaffOverride

        # ✅ فیلتر دسته پرسنل
        # - برای assistant → فقط staff_category='assistant'
        # - برای بقیه → فقط staff_category='nurse'
        if schedule_type == 'assistant':
            category_filter = Q(staff_category='assistant')
        else:
            category_filter = Q(staff_category='nurse')

        base_staff = list(
            Profile.objects.filter(
                (Q(ward=ward) | Q(additional_wards=ward)) & category_filter
            )
            .exclude(role__in=['head', 'admin', 'supervisor'])
            .select_related('user')
            .distinct()
        )

        # اگر year و month داده شده، حذف‌ها را اعمال کن
        if year and month:
            overrides = ScheduleStaffOverride.objects.filter(
                ward=ward,
                year=int(year),
                month=int(month),
                schedule_type=schedule_type,
            )

            excluded_ids = set(overrides.values_list('staff_id', flat=True))

            if excluded_ids:
                base_staff = [p for p in base_staff if p.user.id not in excluded_ids]
                print(f"🚫 {len(excluded_ids)} پرسنل حذف موقت شده‌اند (schedule_type={schedule_type})")

        return base_staff

    @staticmethod
    def _build_staff_info(profile: Profile) -> StaffInfo:
        full_name = f"{profile.user.first_name} {profile.user.last_name}".strip()
        if not full_name:
            full_name = profile.user.username

        legal_hours, max_hours, min_shifts, max_shifts = (
            ContextBuilder._calculate_legal_hours(profile)
        )

        return StaffInfo(
            id=profile.user.id,
            name=full_name,
            first_name=profile.user.first_name or '',
            last_name=profile.user.last_name or '',
            position=profile.position or '',
            position_label=profile.get_position_display() if hasattr(profile, 'get_position_display') else '',
            shift_type=profile.shift_type or 'سه_نوبتی',
            employment_status=profile.employment_status or 'رسمی',
            work_experience=profile.work_experience or 0,
            legal_hours=legal_hours,
            max_hours=max_hours,
            min_shifts=min_shifts,
            max_shifts=max_shifts,
        )

    @staticmethod
    def _calculate_legal_hours(profile: Profile) -> tuple:
        import math

        work_experience = profile.work_experience or 0
        shift_type = profile.shift_type or 'سه_نوبتی'

        base_hours = 192

        if work_experience > 16:
            reduction = 5 * 4.33
        elif 12 <= work_experience <= 16:
            reduction = 4 * 4.33
        elif 8 <= work_experience < 12:
            reduction = 3 * 4.33
        elif 4 <= work_experience < 8:
            reduction = 2 * 4.33
        else:
            reduction = 1 * 4.33

        shift_reduction = 4.33 if shift_type == 'سه_نوبتی' else 0

        legal_hours = base_hours - reduction - shift_reduction
        max_hours = legal_hours + 80

        min_shifts = math.ceil(legal_hours / 10)
        max_shifts = math.floor(max_hours / 10)

        return (
            round(legal_hours, 2),
            round(max_hours, 2),
            min_shifts,
            max_shifts,
        )

    @staticmethod
    def _get_requests(ward: Ward, year: int, month: int) -> Dict[int, Dict[int, str]]:
        month_prefix = f"{year}-{str(month).zfill(2)}"

        requests = ShiftRequest.objects.filter(
            ward=ward,
            request_date__startswith=month_prefix,
        ).select_related('user', 'shift_code')

        result: Dict[int, Dict[int, str]] = {}
        for req in requests:
            try:
                day = int(req.request_date.split('-')[2])
            except (IndexError, ValueError):
                continue

            staff_id = req.user.id
            if staff_id not in result:
                result[staff_id] = {}

            if req.shift_code:
                result[staff_id][day] = req.shift_code.code
            else:
                result[staff_id][day] = '-'

        return result

    @staticmethod
    def _get_previous_month_last_day(ward: Ward, year: int, month: int) -> Dict[int, str]:
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1

        prev_days = ContextBuilder._get_days_in_month(prev_year, prev_month)
        prev_month_prefix = f"{prev_year}-{str(prev_month).zfill(2)}"

        schedules = FinalSchedule.objects.filter(
            ward=ward,
            schedule_date__startswith=prev_month_prefix,
            schedule_type='main',   # فقط main برای پیوستگی
        ).select_related('assigned_staff', 'shift_code')

        result: Dict[int, str] = {}
        for fs in schedules:
            try:
                day = int(fs.schedule_date.split('-')[2])
            except (IndexError, ValueError):
                continue

            if day == prev_days:
                if fs.shift_code:
                    result[fs.assigned_staff.id] = fs.shift_code.code

        return result

    # ============================================================
    # Public Builders
    # ============================================================

    @classmethod
    def build_for_main(cls, ward: Ward, year: int, month: int) -> ScheduleContext:
        """ساخت Context برای برنامه اصلی"""
        return cls._build_for_independent(
            ward=ward, year=year, month=month,
            schedule_type='main',
        )

    # ✅ جدید: build_for_assistant
    @classmethod
    def build_for_assistant(cls, ward: Ward, year: int, month: int) -> ScheduleContext:
        """
        ساخت Context برای برنامه کمک پرستار.
        - مستقل از main
        - target از SpecialScheduleConfig
        """
        return cls._build_for_independent(
            ward=ward, year=year, month=month,
            schedule_type='assistant',
        )

    @classmethod
    def _build_for_independent(
        cls, ward: Ward, year: int, month: int, schedule_type: str,
    ) -> ScheduleContext:
        """
        بیلدر مشترک main و assistant.
        هر دو مستقل‌اند و فقط targetشون فرق داره.
        """
        days_in_month = cls._get_days_in_month(year, month)
        staff_profiles = cls._get_staff(ward, year, month, schedule_type)
        staff: Dict[int, StaffInfo] = {}
        for profile in staff_profiles:
            staff[profile.user.id] = cls._build_staff_info(profile)

        # ✅ تعیین target
        if schedule_type == 'assistant':
            # از SpecialScheduleConfig
            config = SpecialScheduleConfig.objects.filter(
                ward=ward, schedule_type='assistant'
            ).first()

            if config:
                targets = {
                    'M': config.min_staff_morning if config.min_staff_morning is not None else 1,
                    'E': config.min_staff_evening if config.min_staff_evening is not None else 1,
                    'N': config.min_staff_night if config.min_staff_night is not None else 1,
                }
                holiday_targets = {
                    'M': config.holiday_min_staff_morning if config.holiday_min_staff_morning is not None else 1,
                    'E': config.holiday_min_staff_evening if config.holiday_min_staff_evening is not None else 1,
                    'N': config.holiday_min_staff_night if config.holiday_min_staff_night is not None else 1,
                }
            else:
                # پیش‌فرض: ۱ نفر هر شیفت
                targets = {'M': 1, 'E': 1, 'N': 1}
                holiday_targets = {'M': 1, 'E': 1, 'N': 1}
        else:
            # main: از Ward
            targets = {
                'M': ward.min_staff_morning if ward.min_staff_morning is not None else 4,
                'E': ward.min_staff_evening if ward.min_staff_evening is not None else 4,
                'N': ward.min_staff_night if ward.min_staff_night is not None else 3,
            }
            holiday_targets = {
                'M': ward.holiday_min_staff_morning if ward.holiday_min_staff_morning is not None else 2,
                'E': ward.holiday_min_staff_evening if ward.holiday_min_staff_evening is not None else 2,
                'N': ward.holiday_min_staff_night if ward.holiday_min_staff_night is not None else 2,
            }

        shift_codes = list(
            ward.active_shift_codes.filter(is_active=True)
            .values_list('code', flat=True)
        )
        if not shift_codes:
            shift_codes = ['M', 'E', 'N', 'H', '-']

        # ✅ پیوستگی ماه قبل — فقط برای main
        previous_month_last_day = {}
        if schedule_type == 'main':
            previous_month_last_day = cls._get_previous_month_last_day(ward, year, month)

        return ScheduleContext(
            ward_id=ward.id,
            ward_name=ward.name,
            year=year,
            month=month,
            days_in_month=days_in_month,
            schedule_type=schedule_type,
            staff=staff,
            schedule={},
            requests=cls._get_requests(ward, year, month),
            holidays=cls._get_holidays(year, month),
            weekend_days=cls._get_weekend_days(year, month, days_in_month),
            targets=targets,
            holiday_targets=holiday_targets,
            previous_month_last_day=previous_month_last_day,
            shift_codes=shift_codes,
        )

    @classmethod
    def build_for_oncall(
        cls, ward, year, month,
        main_schedule_data=None,
        main_schedule_status=None,
        main_schedule_id=None,
    ) -> ScheduleContext:
        """ساخت Context برای برنامه آنکالی"""
        return cls._build_for_dependent(
            ward=ward, year=year, month=month,
            schedule_type='oncall',
            main_schedule_data=main_schedule_data,
            main_schedule_status=main_schedule_status,
            main_schedule_id=main_schedule_id,
        )

    @classmethod
    def build_for_crisis(
        cls, ward, year, month,
        main_schedule_data=None,
        main_schedule_status=None,
        main_schedule_id=None,
    ) -> ScheduleContext:
        """ساخت Context برای برنامه بحران"""
        return cls._build_for_dependent(
            ward=ward, year=year, month=month,
            schedule_type='crisis',
            main_schedule_data=main_schedule_data,
            main_schedule_status=main_schedule_status,
            main_schedule_id=main_schedule_id,
        )

    @classmethod
    def _build_for_dependent(
        cls,
        ward: Ward,
        year: int,
        month: int,
        schedule_type: str,
        main_schedule_data: Optional[Dict[int, Dict[int, str]]],
        main_schedule_status: Optional[str],
        main_schedule_id: Optional[int],
    ) -> ScheduleContext:
        """بیلدر مشترک oncall/crisis"""
        days_in_month = cls._get_days_in_month(year, month)
        staff_profiles = cls._get_staff(ward, year, month, schedule_type)

        staff: Dict[int, StaffInfo] = {}
        for profile in staff_profiles:
            staff[profile.user.id] = cls._build_staff_info(profile)

        # ✅ چک SpecialScheduleConfig
        config = SpecialScheduleConfig.objects.filter(
            ward=ward,
            schedule_type=schedule_type,
        ).first()

        if config:
            targets = {
                'M': config.min_staff_morning if config.min_staff_morning is not None else 0,
                'E': config.min_staff_evening if config.min_staff_evening is not None else 0,
                'N': config.min_staff_night if config.min_staff_night is not None else 0,
            }
            holiday_targets = {
                'M': config.holiday_min_staff_morning if config.holiday_min_staff_morning is not None else 0,
                'E': config.holiday_min_staff_evening if config.holiday_min_staff_evening is not None else 0,
                'N': config.holiday_min_staff_night if config.holiday_min_staff_night is not None else 0,
            }
            special_config_dict = {
                'min_staff_morning': config.min_staff_morning,
                'min_staff_evening': config.min_staff_evening,
                'min_staff_night': config.min_staff_night,
                'holiday_min_staff_morning': config.holiday_min_staff_morning,
                'holiday_min_staff_evening': config.holiday_min_staff_evening,
                'holiday_min_staff_night': config.holiday_min_staff_night,
            }
        else:
            targets = {'M': 0, 'E': 0, 'N': 0}
            holiday_targets = {'M': 0, 'E': 0, 'N': 0}
            special_config_dict = None

        shift_codes = list(
            ward.active_shift_codes.filter(is_active=True)
            .values_list('code', flat=True)
        )
        if not shift_codes:
            shift_codes = ['M', 'E', 'N', 'H', '-']

        return ScheduleContext(
            ward_id=ward.id,
            ward_name=ward.name,
            year=year,
            month=month,
            days_in_month=days_in_month,
            schedule_type=schedule_type,
            staff=staff,
            schedule={},
            requests=cls._get_requests(ward, year, month),
            holidays=cls._get_holidays(year, month),
            weekend_days=cls._get_weekend_days(year, month, days_in_month),
            targets=targets,
            holiday_targets=holiday_targets,
            previous_month_last_day={},
            shift_codes=shift_codes,
            main_schedule=main_schedule_data or {},
            main_schedule_status=main_schedule_status,
            main_schedule_id=main_schedule_id,
            special_config=special_config_dict,
        )

    # ============================================================
    # Helper: استخراج main
    # ============================================================

    @staticmethod
    def extract_main_schedule_from_final(
        ward: Ward, year: int, month: int,
    ) -> Dict[int, Dict[int, str]]:
        """استخراج برنامه اصلی از FinalSchedule"""
        month_prefix = f"{year}-{str(month).zfill(2)}"

        schedules = FinalSchedule.objects.filter(
            ward=ward,
            schedule_date__startswith=month_prefix,
            schedule_type='main',
        ).select_related('assigned_staff', 'shift_code')

        result: Dict[int, Dict[int, str]] = {}
        for fs in schedules:
            try:
                day = int(fs.schedule_date.split('-')[2])
            except (IndexError, ValueError):
                continue

            staff_id = fs.assigned_staff.id
            if staff_id not in result:
                result[staff_id] = {}

            if fs.shift_code:
                result[staff_id][day] = fs.shift_code.code
            else:
                result[staff_id][day] = '-'

        return result

    @staticmethod
    def get_main_schedule_status(ward: Ward, year: int, month: int) -> Optional[str]:
        """گرفتن وضعیت برنامه اصلی"""
        from api.models import MonthlyScheduleStatus

        status_obj = MonthlyScheduleStatus.objects.filter(
            ward=ward,
            year=year,
            month=month,
            schedule_type='main',
        ).first()

        if status_obj:
            return status_obj.status

        month_prefix = f"{year}-{str(month).zfill(2)}"
        first_fs = FinalSchedule.objects.filter(
            ward=ward,
            schedule_date__startswith=month_prefix,
            schedule_type='main',
        ).first()

        if first_fs:
            return first_fs.status

        return None