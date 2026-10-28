# ai_module/rules/crisis/no_conflict_with_main.py
from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class CrisisNoConflictWithMain(Rule):
    """عدم تداخل بحران با برنامه اصلی"""
    
    code = 'crisis_no_conflict_with_main'
    name = 'عدم تداخل بحران با برنامه اصلی'
    description = 'شیفت بحران نباید با شیفت برنامه اصلی تداخل داشته باشد'
    category = 'hard'
    severity = 'critical'
    default_weight = 150
    applicable_schedule_types = ['crisis']
    
    def __init__(self, forbid_after_night: bool = True):
        super().__init__(forbid_after_night=forbid_after_night)
        self.forbid_after_night = forbid_after_night
    
    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []
        
        for staff_id, staff in context.staff.items():
            crisis_schedule = context.get_staff_schedule(staff_id)
            
            for day in range(1, context.days_in_month + 1):
                crisis_shift = crisis_schedule.get(day, '')
                
                if not crisis_shift or crisis_shift in ('-', 'H', 'S', 'off'):
                    continue
                
                # after night
                if self.forbid_after_night and day > 1:
                    prev_main = context.get_main_schedule_shift(staff_id, day - 1)
                    if 'N' in prev_main:
                        violations.append(self.make_violation(
                            message=f"{staff.name} روز {day-1} شب main، روز {day} بحران {crisis_shift}.",
                            staff_id=staff_id,
                            staff_name=staff.name,
                            day=day,
                        ))
                        continue
                
                main_shift = context.get_main_schedule_shift(staff_id, day)
                
                if not main_shift or main_shift in ('-', 'H', 'S', 'off'):
                    continue
                
                # چک تداخل
                main_shifts = set(c for c in main_shift if c in ('M', 'E', 'N'))
                crisis_shifts = set(c for c in crisis_shift if c in ('M', 'E', 'N'))
                
                if main_shifts & crisis_shifts:
                    violations.append(self.make_violation(
                        message=(
                            f"{staff.name} روز {day}: "
                            f"main = {main_shift}، crisis = {crisis_shift} — تداخل"
                        ),
                        staff_id=staff_id,
                        staff_name=staff.name,
                        day=day,
                    ))
        
        return RuleResult(
            self.code,
            len(violations) == 0,
            violations,
            100.0 if not violations else max(0, 100 - len(violations) * 30),
        )