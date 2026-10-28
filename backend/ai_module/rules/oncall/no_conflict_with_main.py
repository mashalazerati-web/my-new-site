# ai_module/rules/oncall/no_conflict_with_main.py
"""
قانون: عدم تداخل آنکالی با برنامه اصلی
"""

from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class OncallNoConflictWithMain(Rule):
    """
    بررسی می‌کند که شیفت آنکالی با شیفت برنامه اصلی تداخل ندارد.
    
    قوانین:
    - اگر main در روز X شب (N) دارد → oncall نمی‌تواند شب باشد
    - اگر main در روز X عصر (E) دارد → oncall نمی‌تواند عصر باشد
    - اگر main در روز X صبح (M) دارد → oncall نمی‌تواند صبح باشد
    
    اجازه دارد:
    - main صبح → oncall عصر یا شب ✅
    - main عصر → oncall صبح یا شب ✅
    - main شب → oncall صبح یا عصر ✅ (اگر خسته نباشد)
    """
    
    code = 'oncall_no_conflict_with_main'
    name = 'عدم تداخل آنکالی با برنامه اصلی'
    description = 'شیفت آنکالی نباید با شیفت برنامه اصلی در یک روز تداخل داشته باشد'
    category = 'hard'
    severity = 'critical'
    default_weight = 150
    applicable_schedule_types = ['oncall']
    
    parameters_schema = {
        'type': 'object',
        'properties': {
            'allow_different_shift': {
                'type': 'boolean',
                'default': True,
                'description': 'آیا می‌تواند شیفت متفاوت در همان روز داشته باشد',
            },
            'forbid_after_night': {
                'type': 'boolean',
                'default': True,
                'description': 'آیا after night ممنوع است',
            },
        },
        'required': [],
    }
    
    def __init__(
        self,
        allow_different_shift: bool = True,
        forbid_after_night: bool = True,
    ):
        super().__init__(
            allow_different_shift=allow_different_shift,
            forbid_after_night=forbid_after_night,
        )
        self.allow_different_shift = allow_different_shift
        self.forbid_after_night = forbid_after_night
    
    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []
        
        for staff_id, staff in context.staff.items():
            oncall_schedule = context.get_staff_schedule(staff_id)
            
            for day in range(1, context.days_in_month + 1):
                oncall_shift = oncall_schedule.get(day, '')
                
                # آف؟
                if not oncall_shift or oncall_shift in ('-', 'H', 'S', 'off'):
                    continue
                
                # main shift
                main_shift = context.get_main_schedule_shift(staff_id, day)
                
                # روز قبل در main شب بود؟
                if self.forbid_after_night and day > 1:
                    prev_main = context.get_main_schedule_shift(staff_id, day - 1)
                    if 'N' in prev_main:
                        violations.append(self.make_violation(
                            message=(
                                f"{staff.name} روز {day-1} در main شب کار کرده، "
                                f"ولی روز {day} آنکالی {oncall_shift} دارد."
                            ),
                            staff_id=staff_id,
                            staff_name=staff.name,
                            day=day,
                            shift=oncall_shift,
                        ))
                        continue
                
                # تداخل شیفت؟
                if not main_shift or main_shift in ('-', 'H', 'S', 'off'):
                    continue
                
                # چک تداخل
                has_conflict = self._has_conflict(main_shift, oncall_shift)
                
                if has_conflict:
                    violations.append(self.make_violation(
                        message=(
                            f"{staff.name} روز {day}: "
                            f"main = {main_shift}، oncall = {oncall_shift} — "
                            f"تداخل شیفت"
                        ),
                        staff_id=staff_id,
                        staff_name=staff.name,
                        day=day,
                        shift=oncall_shift,
                        main_shift=main_shift,
                    ))
        
        return RuleResult(
            rule_code=self.code,
            is_satisfied=len(violations) == 0,
            violations=violations,
            score=100.0 if not violations else max(0, 100 - len(violations) * 30),
        )
    
    def _has_conflict(self, main_shift: str, oncall_shift: str) -> bool:
        """
        بررسی تداخل.
        
        مثال:
        - main='M', oncall='M' → تداخل ✅
        - main='M', oncall='E' → OK ❌ (تداخل ندارد)
        - main='M', oncall='N' → OK
        - main='E', oncall='E' → تداخل ✅
        - main='N', oncall='N' → تداخل ✅
        - main='MN', oncall='M' → تداخل (چون main هم صبح دارد)
        - main='MN', oncall='E' → OK
        """
        # استخراج شیفت‌ها از main
        main_shifts = set(c for c in main_shift if c in ('M', 'E', 'N'))
        
        # استخراج شیفت‌ها از oncall
        oncall_shifts = set(c for c in oncall_shift if c in ('M', 'E', 'N'))
        
        # تداخل = اشتراک
        return bool(main_shifts & oncall_shifts)