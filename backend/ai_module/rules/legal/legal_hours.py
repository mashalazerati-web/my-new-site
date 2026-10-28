# ai_module/rules/legal/legal_hours.py
"""
قانون: رعایت ساعات قانونی کار
"""

from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class LegalHours(Rule):
    """
    بررسی می‌کند که هر پرستار در محدوده ساعات قانونی کار می‌کند.

    هر شیفت معادل 8 ساعت در نظر گرفته می‌شود.
    """

    code = 'legal_hours'
    name = 'ساعات قانونی کار'
    description = 'رعایت حداقل و حداکثر ساعات قانونی کار'
    category = 'legal'
    severity = 'high'
    default_weight = 80
    # ✅ assistant اضافه شد
    applicable_schedule_types = ['main', 'oncall', 'crisis', 'assistant']

    # ساعات هر شیفت
    SHIFT_HOURS = {
        'M': 7,
        'E': 7,
        'N': 13,
    }

    parameters_schema = {
        'type': 'object',
        'properties': {
            'enforce_min': {
                'type': 'boolean',
                'default': True,
                'description': 'آیا حداقل ساعات اجرا شود',
            },
            'enforce_max': {
                'type': 'boolean',
                'default': True,
                'description': 'آیا حداکثر ساعات اجرا شود',
            },
            'hours_tolerance': {
                'type': 'integer',
                'default': 8,
                'description': 'تلورانس ساعات (برای انعطاف)',
            },
        },
        'required': [],
    }

    def __init__(
        self,
        enforce_min: bool = True,
        enforce_max: bool = True,
        hours_tolerance: int = 8,
    ):
        super().__init__(
            enforce_min=enforce_min,
            enforce_max=enforce_max,
            hours_tolerance=hours_tolerance,
        )
        self.enforce_min = enforce_min
        self.enforce_max = enforce_max
        self.hours_tolerance = hours_tolerance

    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []

        for staff_id, staff in context.staff.items():
            schedule = context.get_staff_schedule(staff_id)

            # محاسبه ساعات
            total_hours = 0
            for day in range(1, context.days_in_month + 1):
                shift = schedule.get(day, '')
                if not shift or shift in ('-', 'H', 'S', 'off'):
                    continue

                # شمارش ساعات بر اساس حروف
                for char in shift:
                    if char in self.SHIFT_HOURS:
                        total_hours += self.SHIFT_HOURS[char]

            # چک حداقل
            if self.enforce_min:
                min_hours = staff.legal_hours - self.hours_tolerance
                if total_hours < min_hours:
                    violations.append(self.make_violation(
                        message=(
                            f"{staff.name}: {total_hours} ساعت کار کرده "
                            f"(حداقل مجاز: {min_hours:.0f})"
                        ),
                        staff_id=staff_id,
                        staff_name=staff.name,
                        actual_hours=total_hours,
                        min_required=min_hours,
                        severity='high',
                    ))

            # چک حداکثر
            if self.enforce_max:
                max_hours = staff.max_hours + self.hours_tolerance
                if total_hours > max_hours:
                    violations.append(self.make_violation(
                        message=(
                            f"{staff.name}: {total_hours} ساعت کار کرده "
                            f"(حداکثر مجاز: {max_hours:.0f})"
                        ),
                        staff_id=staff_id,
                        staff_name=staff.name,
                        actual_hours=total_hours,
                        max_allowed=max_hours,
                        severity='high',
                    ))

        return RuleResult(
            rule_code=self.code,
            is_satisfied=len(violations) == 0,
            violations=violations,
            score=100.0 if not violations else max(0, 100 - len(violations) * 15),
        )