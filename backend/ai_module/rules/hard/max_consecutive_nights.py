# ai_module/rules/hard/max_consecutive_nights.py
"""
قانون: حداکثر شب‌های متوالی
"""

from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class MaxConsecutiveNights(Rule):
    """
    بررسی می‌کند که هیچ پرستاری بیش از N شب متوالی کار نکند.

    مثال:
        rule = MaxConsecutiveNights(max_nights=2)
        result = rule.evaluate(context)
    """

    code = 'max_consecutive_nights'
    name = 'حداکثر شب‌های متوالی'
    description = 'هر پرستار حداکثر می‌تواند N شب پشت سر هم کار کند'
    category = 'hard'
    severity = 'high'
    default_weight = 100
    # ✅ assistant اضافه شد
    applicable_schedule_types = ['main', 'oncall', 'crisis', 'assistant']

    parameters_schema = {
        'type': 'object',
        'properties': {
            'max_nights': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 7,
                'default': 2,
                'description': 'حداکثر تعداد شب‌های متوالی',
            },
        },
        'required': ['max_nights'],
    }

    def __init__(self, max_nights: int = 2):
        super().__init__(max_nights=max_nights)
        self.max_nights = max_nights

    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []

        for staff_id, staff in context.staff.items():
            schedule = context.get_staff_schedule(staff_id)

            consecutive = 0
            for day in range(1, context.days_in_month + 1):
                shift = schedule.get(day, '')

                if 'N' in shift:
                    consecutive += 1
                    if consecutive > self.max_nights:
                        violations.append(self.make_violation(
                            message=(
                                f"روز {day}: پرستار {staff.name} "
                                f"{consecutive} شب متوالی کار کرده "
                                f"(حداکثر مجاز: {self.max_nights})"
                            ),
                            staff_id=staff_id,
                            staff_name=staff.name,
                            day=day,
                            shift=shift,
                            consecutive_count=consecutive,
                            max_allowed=self.max_nights,
                        ))
                else:
                    consecutive = 0

        return RuleResult(
            rule_code=self.code,
            is_satisfied=len(violations) == 0,
            violations=violations,
            score=100.0 if not violations else max(0, 100 - len(violations) * 20),
        )