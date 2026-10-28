# ai_module/rules/registry.py
"""
ثبت همه قوانین — نقطه دسترسی مرکزی
"""

from typing import Dict, Type, List, Optional

from .base import Rule

# Hard rules (main)
from .hard.max_consecutive_nights import MaxConsecutiveNights
from .hard.no_work_after_night import NoWorkAfterNight
from .hard.minimum_staff_coverage import MinimumStaffCoverage
from .hard.main_schedule_required import MainScheduleRequired

# Soft rules
from .soft.preferred_shift import PreferredShiftForStaff
from .soft.fair_distribution import FairShiftDistribution

# Legal rules
from .legal.legal_hours import LegalHours

# ✅ Oncall rules
from .oncall.from_main_staff import OncallFromMainStaff
from .oncall.no_conflict_with_main import OncallNoConflictWithMain
from .oncall.no_off_request import OncallNoOffRequest

# ✅ Crisis rules
from .crisis.from_main_staff import CrisisFromMainStaff
from .crisis.no_conflict_with_main import CrisisNoConflictWithMain
from .crisis.no_off_request import CrisisNoOffRequest


class RuleRegistry:
    """
    رجیستری قوانین.
    
    استفاده:
        registry = RuleRegistry()
        rule = registry.create('max_consecutive_nights', max_nights=3)
    """
    
    def __init__(self):
        self._rules: Dict[str, Type[Rule]] = {}
        self._register_builtin_rules()
    
    def _register_builtin_rules(self):
        """ثبت قوانین پیش‌فرض"""
        
        # ============================================
        # Hard rules (main)
        # ============================================
        self.register(MaxConsecutiveNights)
        self.register(NoWorkAfterNight)
        self.register(MinimumStaffCoverage)
        self.register(MainScheduleRequired)
        
        # ============================================
        # Soft rules
        # ============================================
        self.register(PreferredShiftForStaff)
        self.register(FairShiftDistribution)
        
        # ============================================
        # Legal rules
        # ============================================
        self.register(LegalHours)
        
        # ============================================
        # ✅ Oncall rules
        # ============================================
        self.register(OncallFromMainStaff)
        self.register(OncallNoConflictWithMain)
        self.register(OncallNoOffRequest)
        
        # ============================================
        # ✅ Crisis rules
        # ============================================
        self.register(CrisisFromMainStaff)
        self.register(CrisisNoConflictWithMain)
        self.register(CrisisNoOffRequest)
    
    def register(self, rule_class: Type[Rule]):
        """ثبت یک کلاس قانون"""
        if not hasattr(rule_class, 'code'):
            raise ValueError(f"کلاس {rule_class.__name__} باید code داشته باشد")
        self._rules[rule_class.code] = rule_class
    
    def get(self, code: str) -> Optional[Type[Rule]]:
        """گرفتن کلاس قانون بر اساس کد"""
        return self._rules.get(code)
    
    def create(self, code: str, **params) -> Rule:
        """
        ساخت نمونه قانون.
        
        Args:
            code: کد قانون
            **params: پارامترهای قانون
        
        Raises:
            ValueError: اگر قانون پیدا نشود
        """
        rule_class = self._rules.get(code)
        if not rule_class:
            raise ValueError(f"قانون با کد '{code}' پیدا نشد.")
        return rule_class(**params)
    
    def list_codes(self) -> List[str]:
        """لیست کدهای موجود"""
        return list(self._rules.keys())
    
    def get_all_schemas(self) -> List[Dict]:
        """JSON Schema همه قوانین — برای API"""
        return [cls.get_schema() for cls in self._rules.values()]
    
    def get_by_category(self, category: str) -> List[Type[Rule]]:
        """فیلتر بر اساس دسته"""
        return [
            cls for cls in self._rules.values()
            if cls.category == category
        ]
    
    def get_by_schedule_type(self, schedule_type: str) -> List[Type[Rule]]:
        """فیلتر بر اساس نوع برنامه"""
        return [
            cls for cls in self._rules.values()
            if schedule_type in cls.applicable_schedule_types
        ]


# Singleton
_global_registry: Optional[RuleRegistry] = None


def get_rule_registry() -> RuleRegistry:
    """گرفتن رجیستری سراسری"""
    global _global_registry
    if _global_registry is None:
        _global_registry = RuleRegistry()
    return _global_registry