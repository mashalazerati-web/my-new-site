# ai_module/rules/soft/fair_distribution.py
"""
قانون: توزیع عادلانه شیفت‌ها بین پرستاران
"""

import statistics
from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class FairShiftDistribution(Rule):
    """
    توزیع عادلانه شیفت‌ها (به‌ویژه شب و آخر هفته).
    """

    code = 'fair_shift_distribution'
    name = 'توزیع عادلانه شیفت‌ها'
    description = 'شیفت‌ها (به‌ویژه شب و آخر هفته) عادلانه توزیع شوند'
    category = 'soft'
    severity = 'medium'
    default_weight = 20
    # ✅ assistant اضافه شد
    applicable_schedule_types = ['main', 'oncall', 'crisis', 'assistant']

    parameters_schema = {
        'type': 'object',
        'properties': {
            'max_std_dev_nights': {'type': 'number', 'default': 2.0},
            'max_std_dev_total': {'type': 'number', 'default': 3.0},
            'max_std_dev_weekend': {'type': 'number', 'default': 1.5},
            'min_shift_per_staff': {'type': 'integer', 'default': 15},
            'max_shift_per_staff': {'type': 'integer', 'default': 45},
        },
        'required': [],
    }

    def __init__(
        self,
        max_std_dev_nights: float = 2.0,
        max_std_dev_total: float = 3.0,
        max_std_dev_weekend: float = 1.5,
        min_shift_per_staff: int = 15,
        max_shift_per_staff: int = 45,
    ):
        super().__init__(
            max_std_dev_nights=max_std_dev_nights,
            max_std_dev_total=max_std_dev_total,
            max_std_dev_weekend=max_std_dev_weekend,
            min_shift_per_staff=min_shift_per_staff,
            max_shift_per_staff=max_shift_per_staff,
        )
        self.max_std_dev_nights = max_std_dev_nights
        self.max_std_dev_total = max_std_dev_total
        self.max_std_dev_weekend = max_std_dev_weekend
        self.min_shift_per_staff = min_shift_per_staff
        self.max_shift_per_staff = max_shift_per_staff

    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []
        stats = self._calculate_stats(context)

        if not stats:
            return RuleResult(
                rule_code=self.code,
                is_satisfied=True,
                violations=[],
                score=100.0,
            )

        # انحراف معیار
        std_nights = self._stdev([s['nights'] for s in stats.values()])
        std_total = self._stdev([s['total'] for s in stats.values()])
        std_weekends = self._stdev([s['weekends'] for s in stats.values()])

        # چک انحراف شب‌ها
        if std_nights > self.max_std_dev_nights:
            violations.append(self.make_violation(
                message=(
                    f"توزیع شب‌ها ناعادلانه است — "
                    f"انحراف معیار {std_nights:.2f} (حداکثر {self.max_std_dev_nights})"
                ),
                severity='high',
                std_dev=std_nights,
                max_allowed=self.max_std_dev_nights,
            ))

        # چک انحراف آخر هفته
        if std_weekends > self.max_std_dev_weekend:
            violations.append(self.make_violation(
                message=(
                    f"توزیع آخر هفته ناعادلانه است — "
                    f"انحراف معیار {std_weekends:.2f} (حداکثر {self.max_std_dev_weekend})"
                ),
                std_dev=std_weekends,
                max_allowed=self.max_std_dev_weekend,
            ))

        # چک حداقل/حداکثر شیفت
        for staff_id, data in stats.items():
            if data['total'] < self.min_shift_per_staff:
                violations.append(self.make_violation(
                    message=(
                        f"{data['name']}: فقط {data['total']} شیفت دارد "
                        f"(حداقل {self.min_shift_per_staff})"
                    ),
                    staff_id=staff_id,
                    staff_name=data['name'],
                    total_shifts=data['total'],
                    min_required=self.min_shift_per_staff,
                ))

            if data['total'] > self.max_shift_per_staff:
                violations.append(self.make_violation(
                    message=(
                        f"{data['name']}: {data['total']} شیفت دارد "
                        f"(حداکثر {self.max_shift_per_staff})"
                    ),
                    staff_id=staff_id,
                    staff_name=data['name'],
                    total_shifts=data['total'],
                    max_allowed=self.max_shift_per_staff,
                ))

        # امتیاز
        score = 100.0
        score -= min(30, std_nights * 10)
        score -= min(20, std_weekends * 10)
        score -= len([v for v in violations if v.staff_id is not None]) * 5
        score = max(0, score)

        return RuleResult(
            rule_code=self.code,
            is_satisfied=len(violations) == 0,
            violations=violations,
            score=score,
        )

    def _calculate_stats(self, context: ScheduleContext) -> dict:
        """محاسبه آمار برای هر پرستار"""
        stats = {}
        for staff_id, staff in context.staff.items():
            schedule = context.get_staff_schedule(staff_id)

            total = 0
            nights = 0
            weekends = 0

            for day in range(1, context.days_in_month + 1):
                shift = schedule.get(day, '')
                if not shift or shift in ('-', 'H', 'S', 'off'):
                    continue

                total += 1
                if 'N' in shift:
                    nights += 1
                if context.is_weekend(day):
                    weekends += 1

            stats[staff_id] = {
                'name': staff.name,
                'total': total,
                'nights': nights,
                'weekends': weekends,
            }

        return stats

    @staticmethod
    def _stdev(values: list) -> float:
        """انحراف معیار با محافظت"""
        if len(values) < 2:
            return 0.0
        return statistics.stdev(values)