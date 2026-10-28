# ai_module/rules/crisis/no_off_request.py
from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class CrisisNoOffRequest(Rule):
    """عدم بحران برای آف درخواستی"""
    
    code = 'crisis_no_off_request'
    name = 'عدم بحران برای آف درخواستی'
    description = 'کسانی که در main آف/مرخصی دارند، در بحران شرکت نمی‌کنند'
    category = 'hard'
    severity = 'high'
    default_weight = 120
    applicable_schedule_types = ['crisis']
    
    OFF_SHIFTS = {'-', 'H', 'S', 'off'}
    
    def __init__(self, strict_mode: bool = True):
        super().__init__(strict_mode=strict_mode)
        self.strict_mode = strict_mode
    
    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []
        
        for staff_id, staff in context.staff.items():
            crisis_schedule = context.get_staff_schedule(staff_id)
            
            for day in range(1, context.days_in_month + 1):
                crisis_shift = crisis_schedule.get(day, '')
                
                if not crisis_shift or crisis_shift in self.OFF_SHIFTS:
                    continue
                
                main_shift = context.get_main_schedule_shift(staff_id, day)
                
                if main_shift in self.OFF_SHIFTS:
                    violations.append(self.make_violation(
                        message=f"{staff.name} روز {day} در main آف/مرخصی دارد، اما بحران {crisis_shift} دارد.",
                        staff_id=staff_id,
                        staff_name=staff.name,
                        day=day,
                    ))
                    continue
                
                if self.strict_mode and staff_id in context.requests:
                    requested = context.requests[staff_id].get(day)
                    if requested and requested in self.OFF_SHIFTS:
                        violations.append(self.make_violation(
                            message=f"{staff.name} روز {day} درخواست آف دارد، اما بحران {crisis_shift} دارد.",
                            staff_id=staff_id,
                            staff_name=staff.name,
                            day=day,
                        ))
        
        return RuleResult(
            self.code,
            len(violations) == 0,
            violations,
            100.0 if not violations else max(0, 100 - len(violations) * 20),
        )