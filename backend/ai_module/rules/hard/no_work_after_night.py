# ai_module/rules/hard/no_work_after_night.py
"""
قانون: بعد از شب، آف اجباری
"""

from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class NoWorkAfterNight(Rule):
    """
    بررسی می‌کند که بعد از هر شب، پرستار روز بعد آف باشد.
    """

    code = 'no_work_after_night'
    name = 'آف اجباری بعد از شب'
    description = 'بعد از هر شیفت شب، پرستار باید روز بعد استراحت کند'
    category = 'legal'
    severity = 'critical'
    default_weight = 200
    # ✅ assistant اضافه شد
    applicable_schedule_types = ['main', 'oncall', 'crisis', 'assistant']

    parameters_schema = {
        'type': 'object',
        'properties': {
            'allow_holiday_after_night': {
                'type': 'boolean',
                'default': False,
                'description': 'آیا اجازه دارد روز تعطیل بعد از شب کار کند',
            },
            'allow_combined_shifts': {
                'type': 'boolean',
                'default': False,
                'description': 'آیا شیفت ترکیبی (مثل MN) در روز بعد مجاز است',
            },
        },
        'required': [],
    }

    def __init__(
        self,
        allow_holiday_after_night: bool = False,
        allow_combined_shifts: bool = False,
    ):
        super().__init__(
            allow_holiday_after_night=allow_holiday_after_night,
            allow_combined_shifts=allow_combined_shifts,
        )
        self.allow_holiday_after_night = allow_holiday_after_night
        self.allow_combined_shifts = allow_combined_shifts

    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []
        off_shifts = {'-', 'H', 'S', 'off', ''}

        for staff_id, staff in context.staff.items():
            schedule = context.get_staff_schedule(staff_id)

            for day in range(1, context.days_in_month):
                current_shift = schedule.get(day, '')
                next_shift = schedule.get(day + 1, '')

                # چک: شب در روز جاری
                if 'N' not in current_shift:
                    continue

                # آف؟
                if next_shift in off_shifts:
                    continue

                # اگر اجازه داده شده و روز بعد تعطیل است
                if self.allow_holiday_after_night and context.is_holiday_or_weekend(day + 1):
                    continue

                # اگر شیفت ترکیبی مجاز است
                if self.allow_combined_shifts and next_shift.startswith('N'):
                    continue

                violations.append(self.make_violation(
                    message=(
                        f"{staff.name}: روز {day} شب کار کرده، "
                        f"ولی روز {day + 1} شیفت {next_shift} دارد "
                        f"(باید آف باشد)"
                    ),
                    staff_id=staff_id,
                    staff_name=staff.name,
                    day=day + 1,
                    shift=next_shift,
                    previous_day_night=day,
                    previous_shift=current_shift,
                ))

        return RuleResult(
            rule_code=self.code,
            is_satisfied=len(violations) == 0,
            violations=violations,
            score=100.0 if not violations else max(0, 100 - len(violations) * 25),
        )