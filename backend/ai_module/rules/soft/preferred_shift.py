# ai_module/rules/soft/preferred_shift.py
"""
قانون: ترجیح شیفت برای پرستار خاص
"""

from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class PreferredShiftForStaff(Rule):
    """
    بررسی می‌کند که یک پرستار خاص در روزهای مشخصی، شیفت مورد نظرش را دارد.
    
    مثال:
        rule = PreferredShiftForStaff(staff_id=5, preferred_shift='M')
        rule = PreferredShiftForStaff(staff_id=5, preferred_shift='M', days=[1,2,3])
    """
    
    code = 'preferred_shift_for_staff'
    name = 'ترجیح شیفت پرستار'
    description = 'پرستار خاص در روزهای مشخص، شیفت مورد نظر را داشته باشد'
    category = 'soft'
    severity = 'medium'
    default_weight = 30
    applicable_schedule_types = ['main', 'oncall', 'crisis']
    
    parameters_schema = {
        'type': 'object',
        'properties': {
            'staff_id': {'type': 'integer'},
            'preferred_shift': {
                'type': 'string',
                'enum': ['M', 'E', 'N', 'ME', 'MN', 'EN', 'MEN', '-', 'H'],
            },
            'days': {
                'type': 'array',
                'items': {'type': 'integer'},
            },
            'mode': {
                'type': 'string',
                'enum': ['exact', 'includes'],
                'default': 'includes',
            },
            'staff_name': {'type': 'string'},
        },
        'required': ['staff_id', 'preferred_shift'],
    }
    
    def __init__(
        self,
        staff_id: int,
        preferred_shift: str,
        days: list = None,
        mode: str = 'includes',
        staff_name: str = None,
    ):
        super().__init__(
            staff_id=staff_id,
            preferred_shift=preferred_shift,
            days=days,
            mode=mode,
        )
        self.staff_id = staff_id
        self.preferred_shift = preferred_shift
        self.days = set(days) if days else None
        self.mode = mode
        self.staff_name = staff_name
    
    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []
        
        staff = context.staff.get(self.staff_id)
        if not staff:
            return RuleResult(
                rule_code=self.code,
                is_satisfied=True,
                violations=[],
                score=100.0,
            )
        
        schedule = context.get_staff_schedule(self.staff_id)
        target_days = (
            self.days if self.days
            else set(range(1, context.days_in_month + 1))
        )
        
        for day in sorted(target_days):
            if day < 1 or day > context.days_in_month:
                continue
            
            actual = schedule.get(day, '-')
            
            if self._matches(actual):
                continue
            
            violations.append(self.make_violation(
                message=(
                    f"{staff.name} - روز {day}: "
                    f"انتظار {self.preferred_shift}، دریافت {actual}"
                ),
                staff_id=self.staff_id,
                staff_name=staff.name,
                day=day,
                shift=actual,
                expected=self.preferred_shift,
            ))
        
        total_days = len(target_days)
        matched = total_days - len(violations)
        score = (matched / total_days * 100) if total_days > 0 else 100.0
        
        return RuleResult(
            rule_code=self.code,
            is_satisfied=len(violations) == 0,
            violations=violations,
            score=score,
        )
    
    def _matches(self, actual: str) -> bool:
        """آیا شیفت واقعی با ترجیح می‌خواند؟"""
        if self.mode == 'exact':
            return actual == self.preferred_shift
        
        if not actual:
            return False
        
        # mode = 'includes'
        for char in self.preferred_shift:
            if char not in actual:
                return False
        return True