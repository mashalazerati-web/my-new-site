# ai_module/rules/crisis/from_main_staff.py
from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class CrisisFromMainStaff(Rule):
    """منابع بحران فقط از برنامه اصلی"""
    
    code = 'crisis_from_main_staff'
    name = 'منابع بحران از برنامه اصلی'
    description = 'فقط پرسنلی که در برنامه اصلی حضور دارند می‌توانند در بحران شرکت کنند'
    category = 'hard'
    severity = 'high'
    default_weight = 100
    applicable_schedule_types = ['crisis']
    
    def __init__(self, allow_all_staff: bool = False):
        super().__init__(allow_all_staff=allow_all_staff)
        self.allow_all_staff = allow_all_staff
    
    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []
        
        if self.allow_all_staff:
            return RuleResult(self.code, True, [], 100.0)
        
        main_staff_ids = set(context.get_main_schedule_staff_ids())
        
        for staff_id, staff in context.staff.items():
            crisis_schedule = context.get_staff_schedule(staff_id)
            has_shift = any(
                s and s not in ('-', 'H', 'S', 'off')
                for s in crisis_schedule.values()
            )
            
            if has_shift and staff_id not in main_staff_ids:
                violations.append(self.make_violation(
                    message=f"{staff.name} در main نیست، اما در بحران شیفت دارد.",
                    staff_id=staff_id,
                    staff_name=staff.name,
                ))
        
        return RuleResult(
            self.code,
            len(violations) == 0,
            violations,
            100.0 if not violations else max(0, 100 - len(violations) * 25),
        )