# ai_module/services/schedule_service.py
"""
Schedule Service — نسخه ۴.۰ (کامل)
- توزیع عادلانه شب و آف
- سهم داینامیک بر اساس نیاز واقعی
- سه فاز مستقل (شب / روز / آف)
- پشتیبانی از پرامپت با اولویت‌دهی هوشمند
- جلوگیری سخت‌گیرانه از no_work_after_night
- تعادل تجربه‌ی روز-محور: هر روز ترکیبی از پرستاران با سابقه بالا و پایین
- گروه‌بندی سه‌گانه: high_exp, low_exp, blocked
- متعادل‌سازی شب‌ها بین پرستاران بدون پرامپت
- ✅ چیدن سرپرستار (M در روزهای عادی، - در تعطیلات)
- ✅ نیاز صبح با در نظر گرفتن سرپرستار
"""

import time
import copy
from typing import Dict, List, Optional, Any, Tuple

from ai_module.rules import (
    ScheduleContext,
    Rule,
    AggregateResult,
    RuleRegistry,
    get_rule_registry,
)
from ai_module.rules.violations import Violation


class ScheduleService:
    """
    سرویس تولید برنامه — نسخه ۴.۰
    """

    SHIFT_PRIORITY = ['N', 'M', 'E']
    OFF_SHIFTS = {'-', 'H', 'S', 'off', ''}
    LONG_SHIFT_ORDER = ['MN', 'ME', 'EN']

    def __init__(self, registry: Optional[RuleRegistry] = None):
        self.registry = registry or get_rule_registry()

    # ============================================================
    # API اصلی
    # ============================================================

    def generate(self, context, rules, max_iterations=1):
        start_time = time.time()

        hard_rules = [r for r in rules if r.category in ('hard', 'legal')]
        soft_rules = [r for r in rules if r.category == 'soft']

        schedule = self._generate_with_exact_coverage(
            context=context,
            hard_rules=hard_rules,
            soft_rules=soft_rules,
        )

        temp_context = self._clone_context_with_schedule(context, schedule)
        report = self._validate(temp_context, rules)

        elapsed = time.time() - start_time
        schedule_output = self._schedule_to_output(schedule, context)

        return {
            'schedule': schedule_output,
            'report': report.to_dict() if report else None,
            'stats': {
                'elapsed_seconds': round(elapsed, 2),
                'iterations': 1,
                'staff_count': len(context.staff),
                'days_in_month': context.days_in_month,
                'rules_applied': len(rules),
                'hard_rules_count': len(hard_rules),
                'soft_rules_count': len(soft_rules),
                'best_score': round(report.overall_score, 2),
                'schedule_type': context.schedule_type,
            },
        }

    # ============================================================
    # محاسبه سهم عادلانه
    # ============================================================

    def _compute_fair_shares(self, context):
        staff_ids = list(context.staff.keys())
        staff_count = len(staff_ids)

        if staff_count == 0:
            return {}, {}, {}

        total_nights_needed = 0
        total_shifts_needed = 0
        total_weekend_needed = 0

        for day in range(1, context.days_in_month + 1):
            needs = context.get_daily_needs(day)
            day_total = sum(needs.values())
            total_shifts_needed += day_total
            total_nights_needed += needs.get('N', 0)
            if context.is_weekend(day):
                total_weekend_needed += day_total

        weights = {}
        for sid in staff_ids:
            staff = context.staff[sid]
            weights[sid] = max(1, staff.max_shifts)

        total_weight = sum(weights.values())

        fair_nights = {}
        fair_shifts = {}
        fair_weekends = {}

        for sid in staff_ids:
            ratio = weights[sid] / total_weight
            fair_nights[sid] = total_nights_needed * ratio
            fair_shifts[sid] = total_shifts_needed * ratio
            fair_weekends[sid] = total_weekend_needed * ratio

        return fair_nights, fair_shifts, fair_weekends

    # ============================================================
    # میانگین سابقه بخش
    # ============================================================

    def _compute_ward_avg_experience(self, context):
        """میانگین سابقه کاری کل بخش"""
        if not context.staff:
            return 0.0
        total = sum(s.work_experience for s in context.staff.values())
        return total / len(context.staff)

    # ============================================================
    # استخراج پرامپت‌ها
    # ============================================================

    def _extract_prompt_rules(self, soft_rules):
        result = {
            'night_days': {},
            'night_all': set(),
            'morning_days': {},
            'morning_all': set(),
            'evening_days': {},
            'evening_all': set(),
            'off_days': {},
            'no_night_staff': set(),
            'no_morning_staff': set(),
            'no_evening_staff': set(),
        }

        for rule in soft_rules:
            if rule.code != 'preferred_shift_for_staff':
                continue

            sid = rule.staff_id
            shift = rule.preferred_shift
            days = rule.days

            if shift == 'N':
                if days:
                    result['night_days'].setdefault(sid, set()).update(days)
                else:
                    result['night_all'].add(sid)
                result['no_morning_staff'].add(sid)
                result['no_evening_staff'].add(sid)

            elif shift == 'M':
                if days:
                    result['morning_days'].setdefault(sid, set()).update(days)
                else:
                    result['morning_all'].add(sid)
                result['no_night_staff'].add(sid)
                result['no_evening_staff'].add(sid)

            elif shift == 'E':
                if days:
                    result['evening_days'].setdefault(sid, set()).update(days)
                else:
                    result['evening_all'].add(sid)
                result['no_night_staff'].add(sid)
                result['no_morning_staff'].add(sid)

            elif shift in self.OFF_SHIFTS:
                if days:
                    result['off_days'].setdefault(sid, set()).update(days)

        return result

    # ============================================================
    # ✅ فاز ۰.۷: چیدن سرپرستار
    # ============================================================

    def _assign_head_schedule(self, context, schedule):
        """
        چیدن سرپرستار در برنامه:
        - روزهای عادی: M (صبح)
        - جمعه و تعطیلات: - (آف)

        فقط برای:
        - برنامه اصلی (main)
        - بخش اصلی (نه زیربخش)
        """
        from api.models import Ward, Profile

        if context.schedule_type != 'main':
            return

        try:
            ward = Ward.objects.get(id=context.ward_id)
        except Ward.DoesNotExist:
            return

        if ward.parent is not None:
            print(f"⏭️ بخش «{ward.name}» زیربخش است، سرپرستار چیده نمی‌شود")
            return

        head_profile = Profile.objects.filter(ward=ward, role='head').first()
        if not head_profile:
            print(f"⚠️ سرپرستاری برای بخش «{ward.name}» تعریف نشده")
            return

        head_user_id = head_profile.user.id

        # ✅ ذخیره در context برای استفاده در فازهای بعدی
        context.head_user_id = head_user_id

        # ✅ اضافه کردن به context.staff (برای آمار و گزارش)
        if head_user_id not in context.staff:
            from ai_module.rules.context import StaffInfo
            context.staff[head_user_id] = StaffInfo(
                id=head_user_id,
                name=f"{head_profile.user.first_name} {head_profile.user.last_name}".strip() or head_profile.user.username,
                first_name=head_profile.user.first_name or '',
                last_name=head_profile.user.last_name or '',
                position=head_profile.position or '',
                position_label='سرپرستار',
                shift_type='ثابت_صبح',
                employment_status=head_profile.employment_status or '',
                work_experience=head_profile.work_experience or 0,
                legal_hours=150,
                max_hours=230,
                min_shifts=15,
                max_shifts=23,
            )

        working_days = []
        off_days = []

        if head_user_id not in schedule:
            schedule[head_user_id] = {}

        for day in range(1, context.days_in_month + 1):
            is_holiday_or_friday = context.is_holiday_or_weekend(day)

            has_off_request = False
            if head_user_id in context.requests:
                req = context.requests[head_user_id].get(day)
                if req in self.OFF_SHIFTS:
                    has_off_request = True

            if is_holiday_or_friday or has_off_request:
                schedule[head_user_id][day] = '-'
                off_days.append(day)
            else:
                schedule[head_user_id][day] = 'M'
                working_days.append(day)

        print(f"✅ سرپرستار «{head_profile.user.first_name} {head_profile.user.last_name}»:")
        print(f"   - {len(working_days)} روز عادی → M")
        print(f"   - {len(off_days)} روز تعطیل/جمعه/آف → -")

    # ============================================================
    # ✅ متد کمکی: نیاز مؤثر روزانه (با در نظر گرفتن سرپرستار)
    # ============================================================

    def _get_effective_needs(self, context, schedule, day):
        """
        نیاز روزانه با در نظر گرفتن سرپرستار.
        
        اگر سرپرستار در این روز M گرفته، نیاز صبح را ۱ کم می‌کند
        (چون سرپرستار جزو نیاز صبح شمرده می‌شود).
        """
        needs = context.get_daily_needs(day).copy()

        head_user_id = getattr(context, 'head_user_id', None)
        if (
            head_user_id
            and context.schedule_type == 'main'
            and not context.is_holiday_or_weekend(day)
            and schedule.get(head_user_id, {}).get(day) == 'M'
        ):
            needs['M'] = max(0, needs.get('M', 0) - 1)

        return needs

    # ============================================================
    # فاز ۱: تخصیص شب (تجربه-محور)
    # ============================================================

    def _allocate_nights(self, context, schedule, hard_rules, soft_rules, fair_nights):
        """
        تخصیص شب — نسخه ۳.۰
        """
        staff_ids = list(context.staff.keys())
        # ✅ سرپرستار را از تخصیص شب خارج کن
        head_user_id = getattr(context, 'head_user_id', None)
        if head_user_id:
            staff_ids = [sid for sid in staff_ids if sid != head_user_id]

        ward_avg = self._compute_ward_avg_experience(context)

        sorted_by_exp = sorted(
            staff_ids,
            key=lambda sid: -context.staff[sid].work_experience
        )

        prompts = self._extract_prompt_rules(soft_rules)
        night_days = prompts['night_days']
        night_all = prompts['night_all']
        no_night_staff = prompts['no_night_staff']

        high_exp = [
            sid for sid in sorted_by_exp
            if context.staff[sid].work_experience >= ward_avg
            and sid not in no_night_staff
        ]
        low_exp = [
            sid for sid in sorted_by_exp
            if context.staff[sid].work_experience < ward_avg
            and sid not in no_night_staff
        ]
        blocked = [
            sid for sid in sorted_by_exp
            if sid in no_night_staff
        ]

        print(f"👥 گروه‌بندی تجربه:")
        print(f"   میانگین بخش: {ward_avg:.1f} سال")
        print(f"   high_exp: {len(high_exp)} | low_exp: {len(low_exp)} | blocked: {len(blocked)}")

        night_count = {sid: 0 for sid in staff_ids}
        high_idx = 0
        low_idx = 0
        blocked_idx = 0

        for day in range(1, context.days_in_month + 1):
            # ✅ نیاز مؤثر
            needs = self._get_effective_needs(context, schedule, day)
            needed_n = needs.get('N', 0)

            if needed_n == 0:
                continue

            selected = []

            # مرحله ۱: پرامپت‌های شب
            for sid in staff_ids:
                if len(selected) >= needed_n:
                    break
                if sid not in night_days:
                    continue
                if day not in night_days[sid]:
                    continue
                if schedule[sid].get(day):
                    continue

                passes, _ = self._check_hard_rules(
                    context, schedule, sid, day, 'N', hard_rules, soft_rules
                )
                if not passes:
                    continue
                selected.append(sid)

            # مرحله ۲: ترکیب high/low
            remaining = needed_n - len(selected)
            if remaining > 0 and (high_exp or low_exp):
                target_high = remaining // 2
                target_low = remaining - target_high

                if not high_exp:
                    target_high = 0
                    target_low = remaining
                elif not low_exp:
                    target_high = remaining
                    target_low = 0

                added = 0
                attempts = 0
                max_attempts = len(high_exp) * 3 if high_exp else 0
                while added < target_high and attempts < max_attempts:
                    sid = high_exp[high_idx % len(high_exp)]
                    high_idx += 1
                    attempts += 1
                    if sid in selected or schedule[sid].get(day):
                        continue
                    passes, _ = self._check_hard_rules(
                        context, schedule, sid, day, 'N', hard_rules, soft_rules
                    )
                    if not passes:
                        continue
                    selected.append(sid)
                    added += 1

                added = 0
                attempts = 0
                max_attempts = len(low_exp) * 3 if low_exp else 0
                while added < target_low and attempts < max_attempts:
                    sid = low_exp[low_idx % len(low_exp)]
                    low_idx += 1
                    attempts += 1
                    if sid in selected or schedule[sid].get(day):
                        continue
                    passes, _ = self._check_hard_rules(
                        context, schedule, sid, day, 'N', hard_rules, soft_rules
                    )
                    if not passes:
                        continue
                    selected.append(sid)
                    added += 1

            # مرحله ۳: fallback از blocked
            remaining = needed_n - len(selected)
            if remaining > 0 and blocked:
                attempts = 0
                max_attempts = len(blocked) * 3
                while len(selected) < needed_n and attempts < max_attempts:
                    sid = blocked[blocked_idx % len(blocked)]
                    blocked_idx += 1
                    attempts += 1
                    if sid in selected or schedule[sid].get(day):
                        continue
                    passes, _ = self._check_hard_rules(
                        context, schedule, sid, day, 'N', hard_rules, soft_rules
                    )
                    if not passes:
                        continue
                    selected.append(sid)

            # مرحله ۴: از همه
            if len(selected) < needed_n:
                for sid in staff_ids:
                    if len(selected) >= needed_n:
                        break
                    if sid in selected or schedule[sid].get(day):
                        continue
                    passes, _ = self._check_hard_rules(
                        context, schedule, sid, day, 'N', hard_rules, soft_rules
                    )
                    if not passes:
                        continue
                    selected.append(sid)

            for sid in selected[:needed_n]:
                schedule[sid][day] = 'N'
                night_count[sid] += 1

    # ============================================================
    # فاز ۲: تخصیص صبح و عصر
    # ============================================================

    def _allocate_day_shifts(self, context, schedule, hard_rules, soft_rules, fair_shifts):
        staff_ids = list(context.staff.keys())
        # ✅ سرپرستار را از تخصیص صبح/عصر خارج کن
        head_user_id = getattr(context, 'head_user_id', None)
        if head_user_id:
            staff_ids = [sid for sid in staff_ids if sid != head_user_id]

        prompts = self._extract_prompt_rules(soft_rules)

        morning_days = prompts['morning_days']
        morning_all = prompts['morning_all']
        evening_days = prompts['evening_days']
        evening_all = prompts['evening_all']
        no_morning_staff = prompts['no_morning_staff']
        no_evening_staff = prompts['no_evening_staff']

        for day in range(1, context.days_in_month + 1):
            # ✅ نیاز مؤثر با در نظر گرفتن سرپرستار
            needs = self._get_effective_needs(context, schedule, day)

            for shift_type in ['M', 'E']:
                needed = needs.get(shift_type, 0)
                if needed == 0:
                    continue

                candidates = []
                for sid in staff_ids:
                    if schedule[sid].get(day):
                        continue

                    passes, _ = self._check_hard_rules(
                        context, schedule, sid, day, shift_type, hard_rules, soft_rules
                    )
                    if not passes:
                        continue

                    priority = 0

                    if shift_type == 'M':
                        if sid in morning_days and day in morning_days[sid]:
                            priority = 10000
                        elif sid in morning_all:
                            priority = 8000
                        elif sid in morning_days:
                            priority = -100
                        elif sid in no_morning_staff:
                            priority = -10000
                    else:
                        if sid in evening_days and day in evening_days[sid]:
                            priority = 10000
                        elif sid in evening_all:
                            priority = 8000
                        elif sid in evening_days:
                            priority = -100
                        elif sid in no_evening_staff:
                            priority = -10000

                    staff = context.staff[sid]
                    st_bonus = 0
                    if staff.shift_type == f'ثابت_{"صبح" if shift_type == "M" else "عصر"}':
                        st_bonus = 100

                    req_bonus = 0
                    if sid in context.requests:
                        req = context.requests[sid].get(day)
                        if req == shift_type:
                            req_bonus = 50
                        elif req in self.OFF_SHIFTS:
                            req_bonus = -1000

                    current = self._count_staff_shifts(schedule, sid, context)
                    deficit = fair_shifts.get(sid, 0) - current

                    candidates.append((sid, priority + st_bonus + req_bonus, deficit))

                positive = [c for c in candidates if c[1] >= 0]
                negative = [c for c in candidates if c[1] < 0]

                positive.sort(key=lambda x: (-x[1], -x[2]))
                negative.sort(key=lambda x: (-x[2],))

                selected = positive[:needed]

                if len(selected) < needed:
                    remaining = needed - len(selected)
                    selected.extend(negative[:remaining])

                for sid, _, _ in selected:
                    schedule[sid][day] = shift_type

    # ============================================================
    # فاز ۳: حل کمبود با لانگ
    # ============================================================

    def _fill_day_longs_only(self, context, schedule, day, hard_rules, soft_rules):
        # ✅ نیاز مؤثر با در نظر گرفتن سرپرستار
        needs = self._get_effective_needs(context, schedule, day)
        needed_m = needs.get('M', 0)
        needed_e = needs.get('E', 0)
        needed_n = needs.get('N', 0)

        current_m = self._count_shift_in_day(schedule, day, 'M', include_longs=True)
        current_e = self._count_shift_in_day(schedule, day, 'E', include_longs=True)
        current_n = self._count_shift_in_day(schedule, day, 'N', include_longs=True)

        shortage_m = needed_m - current_m
        shortage_e = needed_e - current_e
        shortage_n = needed_n - current_n

        if shortage_m <= 0 and shortage_e <= 0 and shortage_n <= 0:
            return

        for _ in range(10):
            if shortage_m <= 0 and shortage_e <= 0 and shortage_n <= 0:
                break

            gave = self._fill_shortage_with_longs(
                context=context,
                schedule=schedule,
                day=day,
                shortage_m=shortage_m,
                shortage_e=shortage_e,
                shortage_n=shortage_n,
                hard_rules=hard_rules,
                soft_rules=soft_rules,
            )

            if not gave:
                break

            current_m = self._count_shift_in_day(schedule, day, 'M', include_longs=True)
            current_e = self._count_shift_in_day(schedule, day, 'E', include_longs=True)
            current_n = self._count_shift_in_day(schedule, day, 'N', include_longs=True)

            shortage_m = needed_m - current_m
            shortage_e = needed_e - current_e
            shortage_n = needed_n - current_n

    # ============================================================
    # فاز ۴: متعادل‌سازی آف
    # ============================================================

    def _balance_off_days(self, context, schedule, fair_shifts):
        staff_ids = list(context.staff.keys())

        # ✅ سرپرستار را از متعادل‌سازی خارج کن
        head_user_id = getattr(context, 'head_user_id', None)
        if head_user_id:
            staff_ids = [sid for sid in staff_ids if sid != head_user_id]

        shift_counts = {
            sid: self._count_staff_shifts(schedule, sid, context)
            for sid in staff_ids
        }

        over_loaded = [
            sid for sid in staff_ids
            if shift_counts[sid] > fair_shifts.get(sid, 0) + 1
        ]
        under_loaded = [
            sid for sid in staff_ids
            if shift_counts[sid] < fair_shifts.get(sid, 0) - 1
        ]

        over_loaded.sort(key=lambda sid: -shift_counts[sid])
        under_loaded.sort(key=lambda sid: shift_counts[sid])

        for under_sid in under_loaded:
            target = fair_shifts.get(under_sid, 0)

            for day in range(1, context.days_in_month + 1):
                if shift_counts[under_sid] >= target - 1:
                    break

                if schedule[under_sid].get(day) not in (None, '-', 'H'):
                    continue

                if under_sid in context.requests:
                    if context.requests[under_sid].get(day) in self.OFF_SHIFTS:
                        continue

                if day == 1 and under_sid in context.previous_month_last_day:
                    if 'N' in context.previous_month_last_day[under_sid]:
                        continue

                for over_sid in over_loaded:
                    # ✅ سرپرستار را نادیده بگیر
                    if head_user_id and over_sid == head_user_id:
                        continue

                    if shift_counts[over_sid] <= fair_shifts.get(over_sid, 0):
                        continue

                    over_shift = schedule[over_sid].get(day)
                    if not over_shift or over_shift in ('-', 'H'):
                        continue

                    passes, _ = self._check_hard_rules(
                        context, schedule, under_sid, day, over_shift, [], []
                    )
                    if not passes:
                        continue

                    if day > 1:
                        prev = schedule[under_sid].get(day - 1, '')
                        if 'N' in prev and over_shift not in self.OFF_SHIFTS:
                            continue

                    if 'N' in over_shift:
                        next_day = day + 1
                        if next_day <= context.days_in_month:
                            next_shift = schedule[under_sid].get(next_day, '')
                            if next_shift and next_shift not in self.OFF_SHIFTS:
                                continue

                    schedule[under_sid][day] = over_shift
                    schedule[over_sid][day] = '-'
                    shift_counts[under_sid] += 1
                    shift_counts[over_sid] -= 1
                    break

    # ============================================================
    # فاز ۵: متعادل‌سازی شب‌ها
    # ============================================================

    def _balance_nights_by_fairness(self, context, schedule, hard_rules, soft_rules, fair_nights):
        staff_ids = list(context.staff.keys())

        prompts = self._extract_prompt_rules(soft_rules)
        no_night_staff = prompts['no_night_staff']
        night_days = prompts['night_days']
        night_all = prompts['night_all']

        # ✅ سرپرستار را از متعادل‌سازی شب خارج کن
        head_user_id = getattr(context, 'head_user_id', None)

        neutral_staff = [
            sid for sid in staff_ids
            if sid not in no_night_staff
            and sid not in night_days
            and sid not in night_all
            and sid != head_user_id
        ]

        if not neutral_staff:
            return

        night_counts = {
            sid: self._count_staff_nights(schedule, sid, context)
            for sid in neutral_staff
        }

        over_night = [
            sid for sid in neutral_staff
            if night_counts[sid] > fair_nights.get(sid, 0) + 1
        ]
        under_night = [
            sid for sid in neutral_staff
            if night_counts[sid] < fair_nights.get(sid, 0) - 1
        ]

        over_night.sort(key=lambda sid: -night_counts[sid])
        under_night.sort(key=lambda sid: night_counts[sid])

        if not over_night or not under_night:
            return

        print(f"🌙 متعادل‌سازی شب‌ها (بی‌طرف‌ها):")
        print(f"   over_night: {[(sid, night_counts[sid]) for sid in over_night]}")
        print(f"   under_night: {[(sid, night_counts[sid]) for sid in under_night]}")

        for under_sid in under_night:
            target = fair_nights.get(under_sid, 0)

            for day in range(1, context.days_in_month + 1):
                if night_counts[under_sid] >= target - 1:
                    break

                if schedule[under_sid].get(day) not in (None, '-', 'H'):
                    continue

                if day == 1 and under_sid in context.previous_month_last_day:
                    if 'N' in context.previous_month_last_day[under_sid]:
                        continue

                if day > 1:
                    prev = schedule[under_sid].get(day - 1, '')
                    if 'N' in prev:
                        continue

                if day < context.days_in_month:
                    next_shift = schedule[under_sid].get(day + 1, '')
                    if next_shift and next_shift not in self.OFF_SHIFTS:
                        continue

                for over_sid in over_night:
                    if night_counts[over_sid] <= fair_nights.get(over_sid, 0):
                        continue

                    if 'N' not in schedule[over_sid].get(day, ''):
                        continue

                    passes, _ = self._check_hard_rules(
                        context, schedule, under_sid, day, 'N', hard_rules, []
                    )
                    if not passes:
                        continue

                    schedule[under_sid][day] = 'N'
                    schedule[over_sid][day] = '-'
                    night_counts[under_sid] += 1
                    night_counts[over_sid] -= 1
                    break

    # ============================================================
    # ✅ فاز ۵.۹: بازگرداندن سرپرستار به حالت اصلی
    # ============================================================

    def _enforce_head_schedule(self, context, schedule):
        """
        بازگرداندن سرپرستار به حالت اصلی (M در روزهای عادی، - در تعطیلات).
        """
        head_user_id = getattr(context, 'head_user_id', None)
        if not head_user_id:
            return

        if context.schedule_type != 'main':
            return

        if head_user_id not in schedule:
            return

        fixed_days = 0
        for day in range(1, context.days_in_month + 1):
            is_holiday_or_friday = context.is_holiday_or_weekend(day)

            has_off_request = False
            if head_user_id in context.requests:
                req = context.requests[head_user_id].get(day)
                if req in self.OFF_SHIFTS:
                    has_off_request = True

            expected_shift = '-' if (is_holiday_or_friday or has_off_request) else 'M'
            current_shift = schedule[head_user_id].get(day, '-')

            if current_shift != expected_shift:
                schedule[head_user_id][day] = expected_shift
                fixed_days += 1

        if fixed_days > 0:
            print(f"🔒 سرپرستار در {fixed_days} روز به حالت اصلی بازگردانده شد")

    # ============================================================
    # الگوریتم اصلی
    # ============================================================

    def _generate_with_exact_coverage(self, context, hard_rules, soft_rules):
        schedule = {sid: {} for sid in context.staff}

        fair_nights, fair_shifts, fair_weekends = self._compute_fair_shares(context)
        context.fair_nights = fair_nights
        context.fair_shifts = fair_shifts
        context.fair_weekends = fair_weekends

        print("=" * 60)
        print("📊 سهم عادلانه:")
        for sid in list(context.staff.keys())[:5]:
            staff = context.staff[sid]
            print(f"  {staff.name}: "
                  f"شب={fair_nights[sid]:.1f}, "
                  f"کل={fair_shifts[sid]:.1f}, "
                  f"آخر هفته={fair_weekends[sid]:.1f}")
        print("=" * 60)

        # فاز ۰: درخواست‌ها
        for staff_id, staff_requests in context.requests.items():
            for day, requested_shift in staff_requests.items():
                if requested_shift in self.OFF_SHIFTS:
                    schedule[staff_id][day] = requested_shift

        # فاز ۰.۵: شب آخر ماه قبل
        if context.schedule_type == 'main':
            for staff_id, prev_shift in context.previous_month_last_day.items():
                if 'N' in prev_shift:
                    if 1 not in schedule[staff_id]:
                        schedule[staff_id][1] = '-'

        # ✅ فاز ۰.۷: چیدن سرپرستار
        self._assign_head_schedule(context, schedule)

        # فاز ۱: oncall/crisis
        if context.schedule_type in ('oncall', 'crisis'):
            for staff_id in context.staff:
                for day in range(1, context.days_in_month + 1):
                    main_shift = context.get_main_schedule_shift(staff_id, day)
                    if main_shift in self.OFF_SHIFTS:
                        if day not in schedule[staff_id]:
                            schedule[staff_id][day] = '-'
                        continue
                    if day > 1:
                        prev_main = context.get_main_schedule_shift(staff_id, day - 1)
                        if 'N' in prev_main:
                            if day not in schedule[staff_id]:
                                schedule[staff_id][day] = '-'

        # فاز ۲: تخصیص شب
        self._allocate_nights(context, schedule, hard_rules, soft_rules, fair_nights)

        # فاز ۳: تخصیص صبح/عصر
        self._allocate_day_shifts(context, schedule, hard_rules, soft_rules, fair_shifts)

        # فاز ۴: حل کمبود با لانگ
        for day in range(1, context.days_in_month + 1):
            self._fill_day_longs_only(context, schedule, day, hard_rules, soft_rules)

        # فاز ۵: متعادل‌سازی آف
        self._balance_off_days(context, schedule, fair_shifts)

        # فاز ۵.۵: متعادل‌سازی شب‌ها
        self._balance_nights_by_fairness(
            context, schedule, hard_rules, soft_rules, fair_nights
        )

        # ✅ فاز ۵.۹: بازگرداندن سرپرستار
        self._enforce_head_schedule(context, schedule)

        # فاز ۶: پاکسازی
        for staff_id in context.staff:
            for day in range(1, context.days_in_month + 1):
                if day not in schedule[staff_id]:
                    schedule[staff_id][day] = '-'

        return schedule

    # ============================================================
    # Helper: پر کردن کمبود با لانگ
    # ============================================================

    def _fill_shortage_with_longs(
        self, context, schedule, day,
        shortage_m, shortage_e, shortage_n,
        hard_rules, soft_rules
    ):
        gave_something = False
        staff_ids = list(context.staff.keys())
        # ✅ سرپرستار را از کاندیداها خارج کن
        head_user_id = getattr(context, 'head_user_id', None)
        if head_user_id:
            staff_ids = [sid for sid in staff_ids if sid != head_user_id]

        if shortage_m > 0 and shortage_n > 0:
            candidates = self._get_shortage_candidates(
                context, schedule, day, 'MN',
                lambda sid: schedule[sid].get(day) == 'N',
                hard_rules, staff_ids
            )
            for staff_id in candidates:
                if shortage_m <= 0 or shortage_n <= 0:
                    break
                schedule[staff_id][day] = 'MN'
                shortage_m -= 1
                shortage_n -= 1
                gave_something = True

        if shortage_e > 0:
            candidates = self._get_shortage_candidates(
                context, schedule, day, 'ME',
                lambda sid: schedule[sid].get(day) == 'M',
                hard_rules, staff_ids
            )
            for staff_id in candidates:
                if shortage_e <= 0:
                    break
                schedule[staff_id][day] = 'ME'
                shortage_e -= 1
                if shortage_m > 0:
                    shortage_m -= 1
                gave_something = True

        if shortage_n > 0 and shortage_e > 0:
            candidates = self._get_shortage_candidates(
                context, schedule, day, 'EN',
                lambda sid: schedule[sid].get(day) == 'E',
                hard_rules, staff_ids
            )
            for staff_id in candidates:
                if shortage_n <= 0 or shortage_e <= 0:
                    break
                schedule[staff_id][day] = 'EN'
                shortage_n -= 1
                shortage_e -= 1
                gave_something = True

        if shortage_m > 0 and shortage_n > 0:
            candidates = self._get_shortage_candidates(
                context, schedule, day, 'MN',
                lambda sid: not schedule[sid].get(day) or schedule[sid].get(day) in self.OFF_SHIFTS,
                hard_rules, staff_ids
            )
            for staff_id in candidates:
                if shortage_m <= 0 or shortage_n <= 0:
                    break
                schedule[staff_id][day] = 'MN'
                shortage_m -= 1
                shortage_n -= 1
                gave_something = True

        return gave_something

    def _get_shortage_candidates(
        self, context, schedule, day, shift_type, filter_fn, hard_rules, staff_ids
    ):
        candidates = []
        # ✅ سرپرستار را از کاندیداها خارج کن
        head_user_id = getattr(context, 'head_user_id', None)
        if head_user_id:
            staff_ids = [sid for sid in staff_ids if sid != head_user_id]

        for sid in staff_ids:
            if not filter_fn(sid):
                continue
            passes, _ = self._check_hard_rules(
                context, schedule, sid, day, shift_type, hard_rules, []
            )
            if not passes:
                continue
            current = self._count_staff_shifts(schedule, sid, context)
            fair = getattr(context, 'fair_shifts', {}).get(sid, current)
            deficit = fair - current
            candidates.append((sid, deficit))
        candidates.sort(key=lambda x: -x[1])
        return [sid for sid, _ in candidates]

    # ============================================================
    # Helper: پیدا کردن بهترین کاندید
    # ============================================================

    def _find_best_candidate(self, context, schedule, day, shift_type, available, hard_rules, soft_rules):
        if available is None:
            available = []
            for staff_id in context.staff:
                # ✅ سرپرستار را نادیده بگیر
                head_user_id = getattr(context, 'head_user_id', None)
                if head_user_id and staff_id == head_user_id:
                    continue
                current = schedule[staff_id].get(day, '')
                if not current or current in self.OFF_SHIFTS:
                    available.append(staff_id)

        candidates = []
        for staff_id in available:
            current = schedule[staff_id].get(day, '')
            if current and current not in self.OFF_SHIFTS:
                continue

            passes, _ = self._check_hard_rules(
                context, schedule, staff_id, day, shift_type, hard_rules, soft_rules
            )
            if not passes:
                continue

            current_total = self._count_staff_shifts(schedule, staff_id, context)
            fair = getattr(context, 'fair_shifts', {}).get(staff_id, current_total)
            deficit = fair - current_total

            candidates.append((staff_id, deficit))

        if not candidates:
            return None

        candidates.sort(key=lambda x: -x[1])
        return candidates[0][0]

    # ============================================================
    # چک قوانین Hard
    # ============================================================

    def _check_hard_rules(self, context, schedule, staff_id, day, shift_type, hard_rules, soft_rules=None):
        # ✅ سرپرستار: فقط M در روزهای عادی، - در تعطیلات
        head_user_id = getattr(context, 'head_user_id', None)
        if head_user_id and staff_id == head_user_id:
            is_holiday_or_friday = context.is_holiday_or_weekend(day)
            has_off_request = False
            if staff_id in context.requests:
                req = context.requests[staff_id].get(day)
                if req in self.OFF_SHIFTS:
                    has_off_request = True

            expected = '-' if (is_holiday_or_friday or has_off_request) else 'M'

            if shift_type != expected:
                return False, None

        # ۱. بعد از شب
        if day > 1:
            prev = schedule[staff_id].get(day - 1, '')
            if 'N' in prev:
                if shift_type not in self.OFF_SHIFTS:
                    if any(r.code == 'no_work_after_night' for r in hard_rules):
                        return False, None

        # ۲. حداکثر شب متوالی
        if 'N' in shift_type and day > 1:
            max_nights_consec = 2
            for r in hard_rules:
                if r.code == 'max_consecutive_nights':
                    max_nights_consec = r.max_nights
                    break

            consecutive = 0
            d = day - 1
            while d >= 1:
                prev = schedule[staff_id].get(d, '')
                if 'N' in prev:
                    consecutive += 1
                    d -= 1
                else:
                    break

            if shift_type == 'MN':
                if consecutive >= max_nights_consec + 1:
                    return False, None
            else:
                if consecutive >= max_nights_consec:
                    return False, None

        # ۳. حداکثر شب در ماه
        if 'N' in shift_type:
            max_nights = getattr(context, 'max_nights_per_staff', None)
            if max_nights:
                current_nights = self._count_staff_nights(schedule, staff_id, context)
                if current_nights >= max_nights:
                    return False, None

        # ۴. oncall/crisis
        if context.schedule_type in ('oncall', 'crisis'):
            main_shift = context.get_main_schedule_shift(staff_id, day)
            if main_shift and main_shift not in self.OFF_SHIFTS:
                main_shifts = set(c for c in main_shift if c in ('M', 'E', 'N'))
                new_shifts = set(c for c in shift_type if c in ('M', 'E', 'N'))
                if main_shifts & new_shifts:
                    if any(r.code in ('oncall_no_conflict_with_main', 'crisis_no_conflict_with_main') for r in hard_rules):
                        return False, None

            if main_shift in self.OFF_SHIFTS:
                if any(r.code in ('oncall_no_off_request', 'crisis_no_off_request') for r in hard_rules):
                    return False, None

        # ۵. پرامپت آف
        if soft_rules:
            for rule in soft_rules:
                if rule.code != 'preferred_shift_for_staff':
                    continue
                if rule.staff_id != staff_id:
                    continue
                if rule.days and day not in rule.days:
                    continue
                preferred = rule.preferred_shift
                if preferred in self.OFF_SHIFTS:
                    if shift_type not in self.OFF_SHIFTS:
                        return False, None

        return True, None

    # ============================================================
    # Helper
    # ============================================================

    def _count_shift_in_day(self, schedule, day, shift_type, include_longs=False):
        count = 0
        for days in schedule.values():
            cell = days.get(day, '')
            if not cell or cell in self.OFF_SHIFTS:
                continue
            if include_longs:
                if shift_type in cell:
                    count += 1
            else:
                if cell == shift_type:
                    count += 1
        return count

    def _count_staff_shifts(self, schedule, staff_id, context):
        total = 0
        for s in schedule.get(staff_id, {}).values():
            if not s or s in self.OFF_SHIFTS:
                continue
            total += len([c for c in s if c in ('M', 'E', 'N')])
        return total

    def _count_staff_nights(self, schedule, staff_id, context):
        return sum(1 for s in schedule.get(staff_id, {}).values() if 'N' in s)

    def _count_staff_weekend_shifts(self, schedule, staff_id, context):
        return sum(1 for d, s in schedule.get(staff_id, {}).items()
                   if context.is_weekend(d) and s and s not in self.OFF_SHIFTS)

    def _count_staff_longs(self, schedule, staff_id, context):
        count = 0
        for s in schedule.get(staff_id, {}).values():
            if not s or s in self.OFF_SHIFTS:
                continue
            letters = [c for c in s if c in ('M', 'E', 'N')]
            if len(letters) > 1:
                count += 1
        return count

    def _validate(self, context, rules):
        aggregate = AggregateResult()
        for rule in rules:
            if not rule.is_applicable(context.schedule_type):
                continue
            result = rule.evaluate_with_timing(context)
            aggregate.results.append(result)
        aggregate.total_execution_time_ms = sum(r.execution_time_ms for r in aggregate.results)
        return aggregate

    def _clone_context_with_schedule(self, context, schedule):
        new_context = copy.copy(context)
        new_context.schedule = schedule
        return new_context

    def _schedule_to_output(self, schedule, context):
        output = []

        # ✅ پیدا کردن سرپرستار
        head_user_id = getattr(context, 'head_user_id', None)

        # ✅ ردیف سرپرستار (اول)
        if head_user_id and head_user_id in context.staff:
            head_staff = context.staff[head_user_id]
            days_data = []
            total_m = total_e = total_n = total_h = 0
            total_off = 0
            total_off_after_night = 0
            total_longs = 0

            for day in range(1, context.days_in_month + 1):
                shift = schedule.get(head_user_id, {}).get(day, '-')
                days_data.append({'day': day, 'shift': shift})

                if 'M' in shift: total_m += 1
                if 'E' in shift: total_e += 1
                if 'N' in shift: total_n += 1
                if 'H' in shift: total_h += 1

                letters = [c for c in shift if c in ('M', 'E', 'N')]
                if len(letters) > 1:
                    total_longs += 1

                if shift in self.OFF_SHIFTS:
                    if day > 1:
                        prev_shift = schedule.get(head_user_id, {}).get(day - 1, '')
                        if 'N' in prev_shift:
                            total_off_after_night += 1
                        else:
                            total_off += 1
                    else:
                        total_off += 1

            output.append({
                'staff_id': head_user_id,
                'staff_name': head_staff.name,
                'position_label': 'سرپرستار',
                'employment_status': head_staff.employment_status,
                'days': days_data,
                'total_m': total_m,
                'total_e': total_e,
                'total_n': total_n,
                'total_h': total_h,
                'total_off': total_off,
                'total_off_after_night': total_off_after_night,
                'total_longs': total_longs,
                'is_head': True,
            })

        # ✅ بقیه پرسنل
        for staff_id, staff in context.staff.items():
            if head_user_id and staff_id == head_user_id:
                continue

            days_data = []
            total_m = total_e = total_n = total_h = 0
            total_off = 0
            total_off_after_night = 0
            total_longs = 0

            for day in range(1, context.days_in_month + 1):
                shift = schedule.get(staff_id, {}).get(day, '-')
                days_data.append({'day': day, 'shift': shift})

                if 'M' in shift: total_m += 1
                if 'E' in shift: total_e += 1
                if 'N' in shift: total_n += 1
                if 'H' in shift: total_h += 1

                letters = [c for c in shift if c in ('M', 'E', 'N')]
                if len(letters) > 1:
                    total_longs += 1

                if shift in self.OFF_SHIFTS:
                    if day > 1:
                        prev_shift = schedule.get(staff_id, {}).get(day - 1, '')
                        if 'N' in prev_shift:
                            total_off_after_night += 1
                        else:
                            total_off += 1
                    else:
                        total_off += 1

            output.append({
                'staff_id': staff_id,
                'staff_name': staff.name,
                'position_label': staff.position_label,
                'employment_status': staff.employment_status,
                'days': days_data,
                'total_m': total_m,
                'total_e': total_e,
                'total_n': total_n,
                'total_h': total_h,
                'total_off': total_off,
                'total_off_after_night': total_off_after_night,
                'total_longs': total_longs,
                'is_head': False,
            })

        return output