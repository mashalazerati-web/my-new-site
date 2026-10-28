# ai_module/rules/oncall/from_main_staff.py
"""
قانون: منابع آنکالی فقط از پرسنل برنامه اصلی
"""

from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class OncallFromMainStaff(Rule):
    """
    بررسی می‌کند که همه پرسنل آنکالی، در برنامه اصلی حضور دارند.
    """
    
    code = 'oncall_from_main_staff'
    name = 'منابع آنکالی از برنامه اصلی'
    description = 'فقط پرسنلی که در برنامه اصلی حضور دارند می‌توانند آنکالی بگیرند'
    category = 'hard'
    severity = 'high'
    default_weight = 100
    applicable_schedule_types = ['oncall']
    
    parameters_schema = {
        'type': 'object',
        'properties': {
            'allow_all_staff': {
                'type': 'boolean',
                'default': False,
                'description': 'آیا همه پرسنل بخش می‌توانند شرکت کنند',
            },
        },
        'required': [],
    }
    
    def __init__(self, allow_all_staff: bool = False):
        super().__init__(allow_all_staff=allow_all_staff)
        self.allow_all_staff = allow_all_staff
    
    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []
        
        if self.allow_all_staff:
            return RuleResult(
                rule_code=self.code,
                is_satisfied=True,
                violations=[],
                score=100.0,
            )
        
        # پرستاران حاضر در main
        main_staff_ids = set(context.get_main_schedule_staff_ids())
        
        for staff_id, staff in context.staff.items():
            # آیا در oncall شیفت دارد؟
            oncall_schedule = context.get_staff_schedule(staff_id)
            has_oncall_shift = any(
                s and s not in ('-', 'H', 'S', 'off')
                for s in oncall_schedule.values()
            )
            
            if not has_oncall_shift:
                continue
            
            # آیا در main هست؟
            if staff_id not in main_staff_ids:
                violations.append(self.make_violation(
                    message=(
                        f"{staff.name} در برنامه اصلی حضور ندارد، "
                        f"اما در آنکالی شیفت دارد."
                    ),
                    staff_id=staff_id,
                    staff_name=staff.name,
                ))
        
        return RuleResult(
            rule_code=self.code,
            is_satisfied=len(violations) == 0,
            violations=violations,
            score=100.0 if not violations else max(0, 100 - len(violations) * 25),
        )