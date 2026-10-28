# ai_module/rules/oncall/no_off_request.py
"""
قانون: عدم آنکالی برای کسانی که آف/H/S درخواست داده‌اند
"""

from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class OncallNoOffRequest(Rule):
    """
    اگر پرستار در برنامه اصلی درخواست آف (H, S, -) داده،
    نباید آنکالی بگیرد.
    """
    
    code = 'oncall_no_off_request'
    name = 'عدم آنکالی برای آف درخواستی'
    description = 'کسانی که در برنامه اصلی آف/مرخصی درخواست داده‌اند، آنکالی نمی‌گیرند'
    category = 'hard'
    severity = 'high'
    default_weight = 120
    applicable_schedule_types = ['oncall']
    
    OFF_SHIFTS = {'-', 'H', 'S', 'off'}
    
    parameters_schema = {
        'type': 'object',
        'properties': {
            'strict_mode': {
                'type': 'boolean',
                'default': True,
                'description': 'آیا در حالت strict، حتی اگر آف ثابت نشده باشد، آنکالی نمی‌گیرد',
            },
        },
        'required': [],
    }
    
    def __init__(self, strict_mode: bool = True):
        super().__init__(strict_mode=strict_mode)
        self.strict_mode = strict_mode
    
    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []
        
        for staff_id, staff in context.staff.items():
            oncall_schedule = context.get_staff_schedule(staff_id)
            
            for day in range(1, context.days_in_month + 1):
                oncall_shift = oncall_schedule.get(day, '')
                
                # آف در oncall؟
                if not oncall_shift or oncall_shift in self.OFF_SHIFTS:
                    continue
                
                # چک: در main چه وضعیتی دارد؟
                main_shift = context.get_main_schedule_shift(staff_id, day)
                
                # حالت ۱: در main آف رسمی دارد
                if main_shift in self.OFF_SHIFTS:
                    violations.append(self.make_violation(
                        message=(
                            f"{staff.name} روز {day} در main آف/مرخصی دارد "
                            f"({main_shift})، اما آنکالی {oncall_shift} دارد."
                        ),
                        staff_id=staff_id,
                        staff_name=staff.name,
                        day=day,
                        shift=oncall_shift,
                        main_shift=main_shift,
                    ))
                    continue
                
                # حالت ۲: درخواست آف داشته (strict mode)
                if self.strict_mode:
                    if staff_id in context.requests:
                        requested = context.requests[staff_id].get(day)
                        if requested and requested in self.OFF_SHIFTS:
                            violations.append(self.make_violation(
                                message=(
                                    f"{staff.name} روز {day} درخواست آف/مرخصی دارد "
                                    f"({requested})، اما آنکالی {oncall_shift} دارد."
                                ),
                                staff_id=staff_id,
                                staff_name=staff.name,
                                day=day,
                                shift=oncall_shift,
                                requested_shift=requested,
                            ))
        
        return RuleResult(
            rule_code=self.code,
            is_satisfied=len(violations) == 0,
            violations=violations,
            score=100.0 if not violations else max(0, 100 - len(violations) * 20),
        )