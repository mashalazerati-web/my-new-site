# ai_module/ai_engine_ortools.py
"""
موتور تولید برنامه شیفت - نسخه 37.0 (پشتیبانی از special_config برای آنکالی/بحران)
"""

from django.db.models import Q
from api.models import Ward, Profile, FinalSchedule, ShiftCode, Holiday, ShiftRequest, DraftSchedule
from .models import AIRule
from collections import defaultdict
import time
import math
import jdatetime


class ORToolsShiftSchedulingEngine:
    def __init__(self, ward, year, month, rules=None, prompt='', previous_month_last_day_shift=None, special_config=None):
        self.ward = ward
        self.year = year
        self.month = month
        self.rules = rules or []
        self.prompt = prompt or ''
        self.previous_month_last_day_shift = previous_month_last_day_shift or {}
        self.special_config = special_config  # ✅ جدید

        # ✅ شامل بخش اصلی + بخش‌های اضافی
        from django.db.models import Q
        self.profiles = list(
            Profile.objects.filter(
                Q(ward=ward) | Q(additional_wards=ward)
            )
            .exclude(role__in=['head', 'admin', 'supervisor'])
            .select_related('user')
            .distinct()
        )
        
        self.days_in_month = self._get_days_in_month()
        self.shift_codes = list(ShiftCode.objects.filter(ward=ward, is_active=True))
        self.holidays = self._get_holidays()
        self.weekend_days = self._get_weekend_days()
        self.staff_requests = self._get_staff_requests()
        self.staff_drafts = self._get_staff_drafts()
        self.staff_info = self._get_staff_info()
        self.total_staff = len(self.profiles)

        self.active_rules = self._parse_rules()

        # ✅ تعیین اهداف بر اساس نوع برنامه (اصلی / آنکالی / بحران)
        if special_config:
            self.targets = {
                'M': special_config.min_staff_morning,
                'E': special_config.min_staff_evening,
                'N': special_config.min_staff_night,
            }
            self.holiday_targets = {
                'M': special_config.holiday_min_staff_morning,
                'E': special_config.holiday_min_staff_evening,
                'N': special_config.holiday_min_staff_night,
            }
        else:
            self.targets = {
                'M': ward.min_staff_morning,
                'E': ward.min_staff_evening,
                'N': ward.min_staff_night,
            }
            self.holiday_targets = {
                'M': ward.holiday_min_staff_morning,
                'E': ward.holiday_min_staff_evening,
                'N': ward.holiday_min_staff_night,
            }

        self.prompt_commands = self._parse_prompt_safe()
        self.legal_hours_info = self._calculate_legal_hours()

    def _get_days_in_month(self):
        days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
        return days_in_month[self.month - 1]

    def _get_holidays(self):
        month_prefix = f"{self.year}-{str(self.month).zfill(2)}"
        holidays = Holiday.objects.filter(date__startswith=month_prefix).values('date', 'name')
        holidays_dict = {}
        for h in holidays:
            day = int(h['date'].split('-')[2])
            holidays_dict[day] = h['name']
        return holidays_dict

    def _get_weekend_days(self):
        weekend_days = []
        for day in range(1, self.days_in_month + 1):
            try:
                date = jdatetime.date(self.year, self.month, day)
                if date.weekday() == 6:
                    weekend_days.append(day)
            except:
                pass
        return weekend_days

    def _get_staff_requests(self):
        month_prefix = f"{self.year}-{str(self.month).zfill(2)}"
        requests = ShiftRequest.objects.filter(
            ward=self.ward,
            request_date__startswith=month_prefix
        ).select_related('user', 'shift_code')

        staff_requests = defaultdict(dict)
        for req in requests:
            day = int(req.request_date.split('-')[2])
            staff_id = req.user.id
            if req.shift_code:
                staff_requests[staff_id][day] = req.shift_code.code
            else:
                staff_requests[staff_id][day] = 'off'
        return dict(staff_requests)

    def _get_staff_drafts(self):
        month_prefix = f"{self.year}-{str(self.month).zfill(2)}"
        drafts = DraftSchedule.objects.filter(
            ward=self.ward,
            schedule_date__startswith=month_prefix,
            source='manual'
        ).select_related('assigned_staff', 'shift_code')

        staff_drafts = defaultdict(dict)
        for draft in drafts:
            day = int(draft.schedule_date.split('-')[2])
            staff_id = draft.assigned_staff.id
            if draft.shift_code:
                staff_drafts[staff_id][day] = draft.shift_code.code
        return dict(staff_drafts)

    def _get_staff_info(self):
        staff_info = {}
        for profile in self.profiles:
            staff_info[profile.user.id] = {
                'name': f"{profile.user.first_name} {profile.user.last_name}",
                'shift_type': profile.shift_type,
                'work_experience': profile.work_experience,
                'employment_status': profile.employment_status,
                'position_label': profile.get_position_display(),
            }
        return staff_info
        
    def _is_holiday_or_weekend(self, day):
        return day in self.holidays or day in self.weekend_days

    def _get_daily_needs(self, day):
        if self._is_holiday_or_weekend(day):
            return {'M': self.holiday_targets['M'], 'E': self.holiday_targets['E'], 'N': self.holiday_targets['N']}
        else:
            return {'M': self.targets['M'], 'E': self.targets['E'], 'N': self.targets['N']}

    def _calculate_legal_hours(self):
        legal_info = {}
        non_holiday_days = self.days_in_month - len(self.holidays) - len(self.weekend_days)
        base_hours = non_holiday_days * 7

        for profile in self.profiles:
            staff_id = profile.user.id
            work_experience = profile.work_experience or 0
            shift_type = profile.shift_type or 'سه_نوبتی'
            employment_status = profile.employment_status or 'رسمی'

            reduction_by_experience = 0
            if work_experience > 16:
                reduction_by_experience = 5 * 4.33
            elif 12 <= work_experience <= 16:
                reduction_by_experience = 4 * 4.33
            elif 8 <= work_experience < 12:
                reduction_by_experience = 3 * 4.33
            elif 4 <= work_experience < 8:
                reduction_by_experience = 2 * 4.33
            else:
                reduction_by_experience = 1 * 4.33

            reduction_by_shift = 0
            if shift_type == 'سه_نوبتی':
                reduction_by_shift = 1 * 4.33

            legal_hours = base_hours - reduction_by_experience - reduction_by_shift
            max_hours = legal_hours + 80

            legal_info[staff_id] = {
                'legal_hours': round(legal_hours, 2),
                'max_hours': round(max_hours, 2),
                'min_shifts': math.ceil(legal_hours / 10),
                'max_shifts': math.floor(max_hours / 10),
                'employment_status': employment_status
            }

        return legal_info

    def _get_staff_legal_info(self, staff_id):
        return self.legal_hours_info.get(staff_id, {
            'legal_hours': 150, 'max_hours': 230, 'min_shifts': 15, 'max_shifts': 23
        })

    def _parse_rules(self):
        rules_dict = {}
        for rule in self.rules:
            if hasattr(rule, 'name'):
                rules_dict[rule.name] = rule.is_active
        return rules_dict

    def _is_rule_active(self, rule_name):
        return self.active_rules.get(rule_name, False)

    def _parse_prompt_safe(self):
        commands = {
            'preferred_shift': {},
            'preferred_off': set(),
            'notes': []
        }

        if not self.prompt or not self.prompt.strip():
            return commands

        prompt_text = self.prompt.strip()

        staff_names = {}
        for profile in self.profiles:
            full_name = f"{profile.user.first_name} {profile.user.last_name}".strip()
            if full_name:
                staff_names[full_name] = profile.user.id
                if profile.user.first_name:
                    staff_names[profile.user.first_name] = profile.user.id
                if profile.user.last_name:
                    staff_names[profile.user.last_name] = profile.user.id

        for name, staff_id in staff_names.items():
            if name and name in prompt_text:
                if 'صبح' in prompt_text:
                    commands['preferred_shift'][staff_id] = 'M'
                elif 'عصر' in prompt_text:
                    commands['preferred_shift'][staff_id] = 'E'
                elif 'شب' in prompt_text:
                    commands['preferred_shift'][staff_id] = 'N'

                if 'آف' in prompt_text or 'مرخصی' in prompt_text:
                    commands['preferred_off'].add(staff_id)

        return commands

    def _apply_prompt_to_staff(self, staff, day, shift_type, staff_list):
        staff_id = staff['staff_id']

        if staff_id in self.prompt_commands['preferred_shift']:
            preferred = self.prompt_commands['preferred_shift'][staff_id]
            if preferred != shift_type:
                assigned_count = sum(1 for s in staff_list if s['days'].get(day) == preferred)
                if assigned_count < self._get_daily_needs(day).get(preferred, 0):
                    return False

        if staff_id in self.prompt_commands['preferred_off']:
            return False

        return True

    def _apply_rules_to_staff(self, staff, day, shift_type, staff_list):
        staff_id = staff['staff_id']

        if staff_id in self.staff_requests and day in self.staff_requests[staff_id]:
            req_shift = self.staff_requests[staff_id][day]
            if req_shift in ['H', 'S', '-', 'off']:
                if shift_type in ['H', '-', 'S']:
                    return True
                else:
                    return False

        if self._is_rule_active('نوبت کاری فرد در اولویت'):
            st = staff['shift_type']
            if st == 'ثابت_صبح' and shift_type not in ['M', '-', 'H']:
                return False
            if st == 'ثابت_عصر' and shift_type not in ['E', '-', 'H']:
                return False
            if st == 'ثابت_شب' and shift_type not in ['N', '-', 'H']:
                return False

        if self._is_rule_active('حداکثر شیفت'):
            legal = self._get_staff_legal_info(staff['staff_id'])
            if staff['total_shifts'] >= legal['max_shifts']:
                return False

        if self._is_rule_active('تقسیم شیفت‌های آخر هفته') and day in self.weekend_days:
            weekend_count = sum(1 for d, s in staff['days'].items() if d in self.weekend_days and s != '-')
            avg_weekend = sum(
                sum(1 for d, s in st['days'].items() if d in self.weekend_days and s != '-')
                for st in staff_list
            ) / max(len(staff_list), 1)
            if weekend_count > avg_weekend + 1:
                return False

        if not self._apply_prompt_to_staff(staff, day, shift_type, staff_list):
            return False

        return True

    def _check_no_consecutive_nights(self, staff, day, shift_type):
        if day <= 1:
            return True

        prev_shift = staff['days'].get(day - 1, '')
        if 'N' in prev_shift and 'N' in shift_type:
            return False

        return True

    def _generate_schedule_greedy(self):
        days = range(1, self.days_in_month + 1)

        staff_list = []
        for profile in self.profiles:
            staff_id = profile.user.id
            legal = self._get_staff_legal_info(staff_id)
            staff_list.append({
                'staff_id': staff_id,
                'name': self.staff_info.get(staff_id, {}).get('name', f'کاربر {staff_id}'),
                'work_experience': profile.work_experience or 0,
                'shift_type': profile.shift_type or 'سه_نوبتی',
                'employment_status': profile.employment_status or 'رسمی',
                'total_shifts': 0,
                'last_shift': None,
                'days': {},
                'min_shifts': legal['min_shifts'],
                'max_shifts': legal['max_shifts'],
                'legal_hours': legal['legal_hours'],
                'max_hours': legal['max_hours']
            })

        staff_list.sort(key=lambda x: x['work_experience'], reverse=True)

        # فاز ۰: اعمال درخواست‌های H و S (مرخصی/استراحت) - حتمی
        for staff in staff_list:
            staff_id = staff['staff_id']
            if staff_id in self.staff_requests:
                for day, req_shift in self.staff_requests[staff_id].items():
                    if req_shift in ['H', 'S', '-', 'off']:
                        staff['days'][day] = req_shift

        # فاز ۱: چینش روز به روز (دقیقاً به اندازه نیاز)
        for day in days:
            needs = self._get_daily_needs(day)

            # ✅ چینش شب
            needed_night = needs.get('N', 0)
            if needed_night > 0:
                candidates = []
                for staff in staff_list:
                    if staff['shift_type'] not in ['سه_نوبتی', 'ثابت_شب']:
                        continue
                    if day in staff['days']:
                        continue
                    if day > 1 and staff['days'].get(day - 1) == 'N':
                        continue
                    if not self._apply_rules_to_staff(staff, day, 'N', staff_list):
                        continue
                    candidates.append(staff)

                for staff in candidates:
                    staff['days']['night_count'] = sum(1 for d, s in staff['days'].items() if s == 'N')

                candidates.sort(key=lambda x: (x['days'].get('night_count', 0), x['total_shifts']))
                selected = candidates[:needed_night]

                for staff in selected:
                    staff['days'][day] = 'N'
                    staff['total_shifts'] += 1
                    staff['last_shift'] = 'N'
                    staff['days']['night_count'] = staff['days'].get('night_count', 0) + 1

            # ✅ چینش صبح
            needed_morning = needs.get('M', 0)
            if needed_morning > 0:
                candidates = []
                for staff in staff_list:
                    if day in staff['days']:
                        continue
                    if staff['shift_type'] == 'ثابت_شب':
                        continue
                    if staff['shift_type'] == 'ثابت_عصر':
                        continue
                    if day > 1 and staff['days'].get(day - 1) == 'N':
                        continue
                    if not self._apply_rules_to_staff(staff, day, 'M', staff_list):
                        continue
                    candidates.append(staff)

                candidates.sort(key=lambda x: (x['total_shifts'], -x['work_experience']))
                selected = candidates[:needed_morning]

                for staff in selected:
                    staff['days'][day] = 'M'
                    staff['total_shifts'] += 1
                    staff['last_shift'] = 'M'

            # ✅ چینش عصر
            needed_evening = needs.get('E', 0)
            if needed_evening > 0:
                candidates = []
                for staff in staff_list:
                    if day in staff['days']:
                        continue
                    if staff['shift_type'] == 'ثابت_شب':
                        continue
                    if staff['shift_type'] == 'ثابت_صبح':
                        continue
                    if day > 1 and staff['days'].get(day - 1) == 'N':
                        continue
                    if not self._apply_rules_to_staff(staff, day, 'E', staff_list):
                        continue
                    candidates.append(staff)

                candidates.sort(key=lambda x: (x['total_shifts'], -x['work_experience']))
                selected = candidates[:needed_evening]

                for staff in selected:
                    staff['days'][day] = 'E'
                    staff['total_shifts'] += 1
                    staff['last_shift'] = 'E'

        # فاز ۲: عادلانه کردن شیفت‌ها
        shift_counts = {}
        off_counts = {}
        for staff in staff_list:
            staff_id = staff['staff_id']
            shift_count = sum(1 for d, s in staff['days'].items() if s not in ['-', 'H', 'S'])
            off_count = sum(1 for d, s in staff['days'].items() if s in ['-', 'H', 'S'])
            shift_counts[staff_id] = shift_count
            off_counts[staff_id] = off_count

        avg_shift = sum(shift_counts.values()) / max(len(shift_counts), 1)

        # اگر کسی خیلی کم شیفت دارد، به او شیفت بده
        for staff in staff_list:
            staff_id = staff['staff_id']
            if shift_counts[staff_id] < avg_shift - 2:
                empty_days = [d for d in range(1, self.days_in_month + 1) if d not in staff['days']]
                for day in empty_days:
                    if shift_counts[staff_id] >= avg_shift - 2:
                        break
                    needs = self._get_daily_needs(day)
                    if needs['M'] > 0 or needs['E'] > 0 or needs['N'] > 0:
                        if day > 1 and staff['days'].get(day - 1) == 'N':
                            continue
                        if needs['M'] > 0:
                            staff['days'][day] = 'M'
                            shift_counts[staff_id] += 1
                        elif needs['E'] > 0:
                            staff['days'][day] = 'E'
                            shift_counts[staff_id] += 1
                        elif needs['N'] > 0:
                            staff['days'][day] = 'N'
                            shift_counts[staff_id] += 1

        # اگر کسی خیلی زیاد شیفت دارد، از او کم کن
        for staff in staff_list:
            staff_id = staff['staff_id']
            if shift_counts[staff_id] > avg_shift + 2:
                for day, shift in list(staff['days'].items()):
                    if shift_counts[staff_id] <= avg_shift + 2:
                        break
                    if staff_id in self.staff_requests and day in self.staff_requests[staff_id]:
                        req_shift = self.staff_requests[staff_id][day]
                        if req_shift not in ['H', 'S', '-']:
                            continue
                    if staff_id in self.staff_drafts and day in self.staff_drafts[staff_id]:
                        draft_shift = self.staff_drafts[staff_id][day]
                        if draft_shift != '-':
                            continue
                    needs = self._get_daily_needs(day)
                    assigned_count = sum(1 for s in staff_list if s['days'].get(day) == shift)
                    if assigned_count > needs.get(shift, 0):
                        staff['days'][day] = '-'
                        shift_counts[staff_id] -= 1

        # فاز ۳: اعمال برنامه پیش‌نویس سرپرستار (اگر هنوز روز خالی است)
        for staff in staff_list:
            staff_id = staff['staff_id']
            if staff_id in self.staff_drafts:
                for day, draft_shift in self.staff_drafts[staff_id].items():
                    if day not in staff['days']:
                        staff['days'][day] = draft_shift

        # ساخت خروجی نهایی
        result = []
        for staff in staff_list:
            staff_days = []
            for day in days:
                shift = staff['days'].get(day, '-')
                staff_days.append({'day': day, 'shift': shift})

            m_count = sum(1 for d, s in staff['days'].items() if s == 'M')
            e_count = sum(1 for d, s in staff['days'].items() if s == 'E')
            n_count = sum(1 for d, s in staff['days'].items() if s == 'N')

            result.append({
                'staff_id': staff['staff_id'],
                'staff_name': staff['name'],
                'position_label': self.staff_info.get(staff['staff_id'], {}).get('position_label', '-'),
                'employment_status': self.staff_info.get(staff['staff_id'], {}).get('employment_status', '-'),
                'work_experience': staff['work_experience'],
                'min_shifts': staff['min_shifts'],
                'max_shifts': staff['max_shifts'],
                'legal_hours': staff['legal_hours'],
                'max_hours': staff['max_hours'],
                'total_shifts': staff['total_shifts'],
                'm_count': m_count,
                'e_count': e_count,
                'n_count': n_count,
                'days': staff_days
            })

        return result

    def generate_schedule(self):
        if self.total_staff == 0:
            print("⚠️ هیچ پرستاری برای این بخش یافت نشد")
            return []

        print(f"🚀 شروع تولید برنامه برای {self.total_staff} پرستار")
        if self.special_config:
            print(f"📋 نوع برنامه: {self.special_config.get_schedule_type_display()}")
        print(f"📋 پرامپت: {self.prompt[:50] if self.prompt else 'خالی'}")
        print(f"📋 قوانین فعال: {list(self.active_rules.keys())}")
        start_time = time.time()
        schedule = self._generate_schedule_greedy()
        elapsed = time.time() - start_time
        print(f"✅ برنامه در {elapsed:.2f} ثانیه تولید شد")

        return schedule