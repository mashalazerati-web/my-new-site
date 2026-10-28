# ai_module/rules/violations.py
"""
مدل‌های داده برای نقض قوانین و نتایج ارزیابی
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class Severity(str, Enum):
    """شدت نقض قانون"""
    CRITICAL = 'critical'    # نقض قانون قانونی یا سخت — برنامه غیرقابل قبول
    HIGH = 'high'            # نقض جدی — نیاز به بررسی
    MEDIUM = 'medium'        # نقض متوسط — مطلوب نیست
    LOW = 'low'              # نقض جزئی — قابل چشم‌پوشی
    INFO = 'info'            # فقط اطلاعات


class RuleCategory(str, Enum):
    """دسته قانون"""
    HARD = 'hard'            # اجبار (باید رعایت شود)
    SOFT = 'soft'            # ترجیح (وزن‌دار)
    LEGAL = 'legal'          # قانونی (اجباری)


@dataclass
class Violation:
    """
    یک نقض خاص قانون.
    
    Attributes:
        rule_code: کد قانون نقض‌شده
        severity: شدت نقض
        message: پیام فارسی برای نمایش
        staff_id: شناسه پرستار (اختیاری)
        staff_name: نام پرستار (اختیاری)
        day: روز ماه (اختیاری)
        shift: کد شیفت (اختیاری)
        metadata: داده‌های اضافی برای debugging
    """
    rule_code: str
    severity: str
    message: str
    staff_id: Optional[int] = None
    staff_name: Optional[str] = None
    day: Optional[int] = None
    shift: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # اطمینان از اینکه severity یک رشته است
        if isinstance(self.severity, Severity):
            self.severity = self.severity.value
    
    def to_dict(self) -> Dict[str, Any]:
        """تبدیل به dict برای API"""
        return {
            'rule_code': self.rule_code,
            'severity': self.severity,
            'message': self.message,
            'staff_id': self.staff_id,
            'staff_name': self.staff_name,
            'day': self.day,
            'shift': self.shift,
            'metadata': self.metadata,
        }


@dataclass
class RuleResult:
    """
    نتیجه ارزیابی یک قانون.
    
    Attributes:
        rule_code: کد قانون
        is_satisfied: آیا قانون برآورده شده؟
        violations: لیست نقض‌ها (خالی اگر برآورده شده)
        score: امتیاز از 0 تا 100 (برای soft rules)
        execution_time_ms: زمان اجرا
    """
    rule_code: str
    is_satisfied: bool
    violations: List[Violation] = field(default_factory=list)
    score: float = 100.0
    execution_time_ms: float = 0.0
    
    @property
    def violation_count(self) -> int:
        return len(self.violations)
    
    @property
    def has_critical_violations(self) -> bool:
        return any(v.severity == 'critical' for v in self.violations)
    
    @property
    def has_high_violations(self) -> bool:
        return any(v.severity in ('high', 'critical') for v in self.violations)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule_code': self.rule_code,
            'is_satisfied': self.is_satisfied,
            'violation_count': self.violation_count,
            'score': round(self.score, 2),
            'execution_time_ms': round(self.execution_time_ms, 2),
            'violations': [v.to_dict() for v in self.violations],
        }


@dataclass
class AggregateResult:
    """
    نتیجه ارزیابی همه قوانین.
    """
    results: List[RuleResult] = field(default_factory=list)
    total_execution_time_ms: float = 0.0
    
    @property
    def overall_score(self) -> float:
        """امتیاز کلی (میانگین وزنی)"""
        if not self.results:
            return 100.0
        total = sum(r.score for r in self.results)
        return total / len(self.results)
    
    @property
    def total_violations(self) -> int:
        return sum(r.violation_count for r in self.results)
    
    @property
    def all_violations(self) -> List[Violation]:
        violations = []
        for r in self.results:
            violations.extend(r.violations)
        return violations
    
    @property
    def critical_violations(self) -> List[Violation]:
        return [v for v in self.all_violations if v.severity == 'critical']
    
    @property
    def high_violations(self) -> List[Violation]:
        return [v for v in self.all_violations if v.severity == 'high']
    
    @property
    def is_acceptable(self) -> bool:
        """آیا برنامه قابل قبول است؟"""
        return len(self.critical_violations) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_score': round(self.overall_score, 2),
            'total_violations': self.total_violations,
            'critical_violations': len(self.critical_violations),
            'high_violations': len(self.high_violations),
            'is_acceptable': self.is_acceptable,
            'total_execution_time_ms': round(self.total_execution_time_ms, 2),
            'results': [r.to_dict() for r in self.results],
        }