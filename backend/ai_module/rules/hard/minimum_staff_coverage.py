# ai_module/rules/hard/minimum_staff_coverage.py
"""
قانون: حداقل پوشش پرسنل در هر شیفت
"""

from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class MinimumStaffCoverage(Rule):
    """
    بررسی می‌کند که هر روز، تعداد کافی پرسنل در هر شیفت وجود داشته باشد.

    برای main/assistant: hard (نقض جدی)
    برای oncall/crisis: soft (پوشش ناقص قبول است ولی هشدار می‌دهد)
    """

    code = 'minimum_staff_coverage'
    name = 'حداقل پوشش پرسنل'
    description = 'هر روز باید تعداد کافی پرسنل در هر شیفت داشته باشد'
    category = 'hard'   # پیش‌فرض برای main/assistant
    severity = 'critical'
    default_weight = 150
    # ✅ assistant اضافه شد
    applicable_schedule_types = ['main', 'oncall', 'crisis', 'assistant']

    parameters_schema = {
        'type': 'object',
        'properties': {
            'strict': {'type': 'boolean', 'default': True},
            'allow_overcoverage': {'type': 'boolean', 'default': True},
            'max_overcoverage': {'type': 'integer', 'default': 2},
            'soft_for_dependent': {
                'type': 'boolean',
                'default': True,
                'description': 'اگر True باشد، برای oncall/crisis نرم است',
            },
        },
        'required': [],
    }

    def __init__(
        self,
        strict: bool = True,
        allow_overcoverage: bool = True,
        max_overcoverage: int = 2,
        soft_for_dependent: bool = True,
    ):
        super().__init__(
            strict=strict,
            allow_overcoverage=allow_overcoverage,
            max_overcoverage=max_overcoverage,
            soft_for_dependent=soft_for_dependent,
        )
        self.strict = strict
        self.allow_overcoverage = allow_overcoverage
        self.max_overcoverage = max_overcoverage
        self.soft_for_dependent = soft_for_dependent

    def is_applicable(self, schedule_type: str) -> bool:
        """بررسی اعمال قانون"""
        return schedule_type in self.applicable_schedule_types

    def get_severity_for_type(self, schedule_type: str) -> str:
        """
        شدت نقض بر اساس نوع برنامه.
        - main/assistant: critical (جدی)
        - oncall/crisis: low (اطلاعاتی)
        """
        # ✅ assistant هم soft هست (چون برنامه‌ی جانبیه)
        if self.soft_for_dependent and schedule_type in ('oncall', 'crisis', 'assistant'):
            return 'low'
        return self.severity

    def get_category_for_type(self, schedule_type: str) -> str:
        """
        دسته‌بندی بر اساس نوع برنامه.
        - main/assistant: hard
        - oncall/crisis: soft
        """
        # ✅ assistant هم soft هست
        if self.soft_for_dependent and schedule_type in ('oncall', 'crisis', 'assistant'):
            return 'soft'
        return 'hard'

    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []

        # ✅ تعیین شدت بر اساس نوع برنامه
        severity = self.get_severity_for_type(context.schedule_type)
        is_soft = (severity == 'low')

        for day in range(1, context.days_in_month + 1):
            needs = context.get_daily_needs(day)

            # شمارش پرسنل هر شیفت
            actual = {'M': 0, 'E': 0, 'N': 0}
            for staff_id in context.staff:
                shift = context.get_staff_shift(staff_id, day)
                if 'M' in shift: actual['M'] += 1
                if 'E' in shift: actual['E'] += 1
                if 'N' in shift: actual['N'] += 1

            # چک هر شیفت
            for shift_type in ['M', 'E', 'N']:
                needed = needs.get(shift_type, 0)
                actual_count = actual[shift_type]

                # کمبود
                if actual_count < needed:
                    if is_soft:
                        message = (
                            f"روز {day}: کمبود {shift_type} "
                            f"({actual_count}/{needed}) — قابل قبول است"
                        )
                    else:
                        message = (
                            f"روز {day}: کمبود پرسنل {shift_type} "
                            f"({actual_count}/{needed})"
                        )

                    violations.append(self.make_violation(
                        message=message,
                        day=day,
                        shift=shift_type,
                        severity=severity,
                        actual=actual_count,
                        needed=needed,
                        shortage=needed - actual_count,
                    ))

                # اضافه پرسنل
                elif actual_count > needed + self.max_overcoverage:
                    violations.append(self.make_violation(
                        message=(
                            f"روز {day}: اضافه پرسنل {shift_type} "
                            f"({actual_count}/{needed})"
                        ),
                        day=day,
                        shift=shift_type,
                        severity='low',
                        actual=actual_count,
                        needed=needed,
                        surplus=actual_count - needed,
                    ))

        score = self._calculate_score(context)

        return RuleResult(
            rule_code=self.code,
            is_satisfied=len(violations) == 0,
            violations=violations,
            score=score,
        )

    def _calculate_score(self, context: ScheduleContext) -> float:
        """امتیاز بر اساس درصد پوشش"""
        total_needed = 0
        total_matched = 0

        for day in range(1, context.days_in_month + 1):
            needs = context.get_daily_needs(day)
            for shift_type in ['M', 'E', 'N']:
                needed = needs.get(shift_type, 0)
                total_needed += needed

                actual = 0
                for staff_id in context.staff:
                    shift = context.get_staff_shift(staff_id, day)
                    if shift_type in shift:
                        actual += 1

                total_matched += min(actual, needed)

        if total_needed == 0:
            return 100.0

        coverage = (total_matched / total_needed) * 100

        # ✅ برای برنامه‌های جانبی، امتیاز کمتر سخت‌گیرانه
        if context.schedule_type in ('oncall', 'crisis', 'assistant'):
            return max(70, coverage)
        return coverage