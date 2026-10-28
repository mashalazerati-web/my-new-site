# ai_module/rules/base.py
"""
کلاس پایه Rule — همه قوانین از این ارث می‌برند
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import time

from .violations import RuleResult, Violation, Severity, RuleCategory
from .context import ScheduleContext


class Rule(ABC):
    """
    کلاس پایه همه قوانین.
    
    هر قانون:
        - یک کد یکتا دارد (code)
        - پارامتر می‌گیرد (params)
        - متد evaluate را پیاده‌سازی می‌کند
        - ممکن است schedule_type مشخصی داشته باشد
    """
    
    # ============================================
    # Metadata — در زیرکلاس override می‌شوند
    # ============================================
    code: str = 'base_rule'
    name: str = 'قانون پایه'
    description: str = ''
    category: str = RuleCategory.SOFT.value
    severity: str = Severity.MEDIUM.value
    default_weight: int = 10
    
    # ✅ برای oncall/crisis: به کدام انواع برنامه اعمال می‌شود؟
    # ['main'] → فقط main
    # ['main', 'oncall', 'crisis'] → همه
    # ['oncall', 'crisis'] → فقط وابسته‌ها
    applicable_schedule_types: List[str] = ['main', 'oncall', 'crisis']
    
    # JSON Schema پارامترها (برای API)
    parameters_schema: Dict[str, Any] = {}
    
    # ============================================
    # ✅ شیفت‌های لانگ — ثابت‌های کلاس
    # ============================================
    
    # 🎯 ترتیب اولویت شیفت‌های لانگ
    # اول MN، سپس ME، و نهایتاً EN و MEN (بسیار نادر)
    LONG_SHIFT_ORDER: List[str] = ['MN', 'ME', 'EN', 'MEN']
    
    # 🎯 ارزش هر شیفت لانگ (به تعداد شیفت معمولی)
    LONG_SHIFT_VALUES: Dict[str, int] = {
        'MN': 3,   # صبح + شب (۱۶ ساعت + شیفت شب = ۳ شیفت کاری)
        'ME': 2,   # صبح + عصر (۱۶ ساعت = ۲ شیفت)
        'EN': 2,   # عصر + شب (۱۶ ساعت = ۲ شیفت)
        'MEN': 3,  # صبح + عصر + شب (۲۴ ساعت = ۳ شیفت)
    }
    
    # 🎯 توضیحات فارسی برای هر شیفت لانگ
    LONG_SHIFT_LABELS: Dict[str, str] = {
        'MN': 'صبح + شب',
        'ME': 'صبح + عصر',
        'EN': 'عصر + شب',
        'MEN': 'صبح + عصر + شب',
    }
    
    # 🎯 حروف تشکیل‌دهنده هر شیفت (برای تشخیص تداخل)
    SHIFT_LETTERS: Dict[str, List[str]] = {
        'M': ['M'],
        'E': ['E'],
        'N': ['N'],
        'MN': ['M', 'N'],
        'ME': ['M', 'E'],
        'EN': ['E', 'N'],
        'MEN': ['M', 'E', 'N'],
    }
    
    def __init__(self, **params):
        """
        Args:
            **params: پارامترهای قانون
        """
        self.params = params
        self._validate_params()
    
    def _validate_params(self):
        """اعتبارسنجی ساده پارامترها"""
        required = self.parameters_schema.get('required', [])
        for req in required:
            if req not in self.params:
                raise ValueError(
                    f"پارامتر '{req}' برای قانون '{self.code}' الزامی است."
                )
    
    @abstractmethod
    def evaluate(self, context: ScheduleContext) -> RuleResult:
        """
        ارزیابی قانون روی یک برنامه.
        
        Args:
            context: ScheduleContext
        
        Returns:
            RuleResult: نتیجه ارزیابی
        """
        pass
    
    def evaluate_with_timing(self, context: ScheduleContext) -> RuleResult:
        """ارزیابی + اندازه‌گیری زمان"""
        start = time.time()
        result = self.evaluate(context)
        result.execution_time_ms = (time.time() - start) * 1000
        return result
    
    def is_applicable(self, schedule_type: str) -> bool:
        """آیا این قانون برای این نوع برنامه قابل اعمال است؟"""
        return schedule_type in self.applicable_schedule_types
    
    # ============================================
    # Helper methods برای زیرکلاس‌ها
    # ============================================
    
    def make_violation(
        self,
        message: str,
        staff_id: int = None,
        staff_name: str = None,
        day: int = None,
        shift: str = None,
        severity: str = None,
        **metadata,
    ) -> Violation:
        """ساخت یک Violation با مقادیر پیش‌فرض"""
        return Violation(
            rule_code=self.code,
            severity=severity or self.severity,
            message=message,
            staff_id=staff_id,
            staff_name=staff_name,
            day=day,
            shift=shift,
            metadata=metadata,
        )
    
    def get_staff_name(self, context: ScheduleContext, staff_id: int) -> str:
        """گرفتن نام پرستار"""
        staff = context.staff.get(staff_id)
        return staff.name if staff else f"کاربر {staff_id}"
    
    # ============================================
    # ✅ Helper methods برای شیفت‌های لانگ
    # ============================================
    
    @classmethod
    def is_long_shift(cls, shift_code: str) -> bool:
        """آیا این شیفت لانگ است؟"""
        return shift_code in cls.LONG_SHIFT_VALUES
    
    @classmethod
    def get_shift_letters(cls, shift_code: str) -> List[str]:
        """
        حروف تشکیل‌دهنده یک شیفت.
        
        مثال:
            'M' → ['M']
            'MN' → ['M', 'N']
            'MEN' → ['M', 'E', 'N']
        """
        return [c for c in shift_code.upper() if c in ('M', 'E', 'N')]
    
    @classmethod
    def get_shift_value(cls, shift_code: str) -> int:
        """
        ارزش یک شیفت (به تعداد شیفت معمولی).
        
        مثال:
            'M' → 1
            'MN' → 3
            'ME' → 2
            '-' → 0
        """
        if shift_code in cls.OFF_SHIFTS if hasattr(cls, 'OFF_SHIFTS') else {'-', 'H', 'S', 'off', ''}:
            return 0
        
        if shift_code in cls.LONG_SHIFT_VALUES:
            return cls.LONG_SHIFT_VALUES[shift_code]
        
        # شیفت معمولی
        letters = cls.get_shift_letters(shift_code)
        return len(letters) if letters else 0
    
    @classmethod
    def shifts_have_conflict(cls, shift1: str, shift2: str) -> bool:
        """
        آیا دو شیفت با هم تداخل دارند؟
        
        مثال:
            'M' و 'M' → تداخل ✅
            'M' و 'E' → بدون تداخل ❌
            'MN' و 'M' → تداخل (چون هر دو M دارند)
            'MN' و 'E' → بدون تداخل
        """
        letters1 = set(cls.get_shift_letters(shift1))
        letters2 = set(cls.get_shift_letters(shift2))
        
        return bool(letters1 & letters2)
    
    # ============================================
    # Class methods برای factory و API
    # ============================================
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """JSON Schema قانون برای API"""
        return {
            'code': cls.code,
            'name': cls.name,
            'description': cls.description,
            'category': cls.category if isinstance(cls.category, str) else cls.category.value,
            'severity': cls.severity if isinstance(cls.severity, str) else cls.severity.value,
            'default_weight': cls.default_weight,
            'applicable_schedule_types': cls.applicable_schedule_types,
            'parameters_schema': cls.parameters_schema,
        }
    
    def __repr__(self):
        return f"<{self.__class__.__name__} code={self.code} params={self.params}>"