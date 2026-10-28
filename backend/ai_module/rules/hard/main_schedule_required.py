# ai_module/rules/hard/main_schedule_required.py
"""
قانون: پیش‌نیاز برنامه اصلی (فقط برای oncall/crisis)

این قانون تضمین می‌کند که:
1. برنامه اصلی وجود دارد
2. برنامه اصلی در وضعیت قابل قبول است (LOCKED, PENDING_SUPERVISOR, PENDING_MATRON)
3. همه پرسنل oncall/crisis از پرسنل main هستند
"""

from ..base import Rule
from ..violations import RuleResult
from ..context import ScheduleContext


class MainScheduleRequired(Rule):
    """
    قانون مخصوص oncall و crisis:
    برنامه اصلی باید ابتدا تایید شده باشد و پرسنل از main بیایند.
    """
    
    code = 'main_schedule_required'
    name = 'پیش‌نیاز برنامه اصلی'
    description = 'برای تولید oncall/crisis، ابتدا برنامه اصلی باید تایید شود'
    category = 'hard'
    severity = 'critical'
    default_weight = 300
    applicable_schedule_types = ['oncall', 'crisis']   # ← فقط for oncall/crisis
    
    # وضعیت‌های قابل قبول برای برنامه اصلی
    ALLOWED_MAIN_STATUSES = [
        'PENDING_SUPERVISOR',
        'PENDING_MATRON',
        'LOCKED',
    ]
    
    parameters_schema = {
        'type': 'object',
        'properties': {
            'allow_all_staff': {
                'type': 'boolean',
                'default': True,
                'description': 'آیا همه پرسنل بخش می‌توانند در oncall/crisis باشند یا فقط کسانی که در main هستند',
            },
            'min_main_status': {
                'type': 'string',
                'enum': ['PENDING_SUPERVISOR', 'PENDING_MATRON', 'LOCKED'],
                'default': 'PENDING_SUPERVISOR',
                'description': 'حداقل وضعیت قابل قبول برای برنامه اصلی',
            },
        },
        'required': [],
    }
    
    def __init__(
        self,
        allow_all_staff: bool = True,
        min_main_status: str = 'PENDING_SUPERVISOR',
    ):
        super().__init__(
            allow_all_staff=allow_all_staff,
            min_main_status=min_main_status,
        )
        self.allow_all_staff = allow_all_staff
        self.min_main_status = min_main_status
    
    def evaluate(self, context: ScheduleContext) -> RuleResult:
        violations = []
        
        # ============================================
        # چک ۱: آیا برنامه اصلی وجود دارد؟
        # ============================================
        if not context.main_schedule:
            violations.append(self.make_violation(
                message=(
                    "برنامه اصلی هنوز تولید نشده است. "
                    "ابتدا برنامه اصلی را تولید و تایید کنید."
                ),
                metadata={
                    'check': 'main_schedule_exists',
                    'schedule_type': context.schedule_type,
                },
            ))
            return RuleResult(
                rule_code=self.code,
                is_satisfied=False,
                violations=violations,
                score=0.0,
            )
        
        # ============================================
        # چک ۲: آیا برنامه اصلی در وضعیت قابل قبول است؟
        # ============================================
        if context.main_schedule_status:
            if context.main_schedule_status not in self.ALLOWED_MAIN_STATUSES:
                violations.append(self.make_violation(
                    message=(
                        f"برنامه اصلی در وضعیت '{context.main_schedule_status}' است. "
                        f"برای تولید oncall/crisis، ابتدا باید برنامه اصلی تایید شود "
                        f"(وضعیت‌های مجاز: {', '.join(self.ALLOWED_MAIN_STATUSES)})"
                    ),
                    metadata={
                        'check': 'main_status',
                        'current_status': context.main_schedule_status,
                        'allowed_statuses': self.ALLOWED_MAIN_STATUSES,
                    },
                ))
        else:
            # اگر status داده نشده باشد، هشدار می‌دهیم
            violations.append(self.make_violation(
                message=(
                    "وضعیت برنامه اصلی مشخص نیست. "
                    "امکان تولید برنامه وابسته وجود ندارد."
                ),
                metadata={
                    'check': 'main_status_missing',
                },
            ))
        
        # ============================================
        # چک ۳: آیا همه پرسنل oncall/crisis از main هستند؟
        # ============================================
        if not self.allow_all_staff:
            main_staff_ids = set(context.get_main_schedule_staff_ids())
            
            for staff_id, staff in context.staff.items():
                # اگر پرستار در oncall/crisis برنامه دارد ولی در main نیست
                has_schedule = bool(context.get_staff_schedule(staff_id))
                
                if has_schedule and staff_id not in main_staff_ids:
                    violations.append(self.make_violation(
                        message=(
                            f"پرستار {staff.name} در برنامه اصلی حضور ندارد، "
                            f"اما در برنامه {context.schedule_type} شیفت دارد."
                        ),
                        staff_id=staff_id,
                        staff_name=staff.name,
                        metadata={
                            'check': 'staff_not_in_main',
                        },
                    ))
        
        return RuleResult(
            rule_code=self.code,
            is_satisfied=len(violations) == 0,
            violations=violations,
            score=100.0 if not violations else 0.0,
        )