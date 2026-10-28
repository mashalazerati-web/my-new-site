# ai_module/prompt/entities.py
"""
مدل‌های داده برای موجودیت‌های استخراج‌شده از پرامپت
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class ExtractedEntity:
    """موجودیت استخراج‌شده از یک جمله"""
    sentence: str
    pattern_matched: str
    rule_code: str
    parameters: Dict[str, Any]
    confidence: float = 1.0    # 0.0 تا 1.0


@dataclass
class PromptInterpretationResult:
    """
    نتیجه کامل تفسیر پرامپت.
    
    Attributes:
        original_prompt: پرامپت اصلی
        normalized_prompt: پرامپت نرمال‌شده
        sentences: جملات تقسیم‌شده
        matched_entities: موجودیت‌های تطبیق‌داده‌شده
        unmatched_sentences: جملاتی که الگو نخوردند
        rules: قوانین ساخته‌شده (Rule objects)
        warnings: هشدارها
        errors: خطاها
    """
    original_prompt: str = ''
    normalized_prompt: str = ''
    sentences: List[str] = field(default_factory=list)
    matched_entities: List[ExtractedEntity] = field(default_factory=list)
    unmatched_sentences: List[str] = field(default_factory=list)
    rules: List[Any] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def total_sentences(self) -> int:
        return len(self.sentences)
    
    @property
    def matched_sentences(self) -> int:
        return len(self.matched_entities)
    
    @property
    def unmatched_count(self) -> int:
        return len(self.unmatched_sentences)
    
    @property
    def match_rate(self) -> float:
        """درصد تطبیق"""
        if self.total_sentences == 0:
            return 100.0
        return (self.matched_sentences / self.total_sentences) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_prompt': self.original_prompt,
            'normalized_prompt': self.normalized_prompt,
            'sentences': self.sentences,
            'total_sentences': self.total_sentences,
            'matched_sentences': self.matched_sentences,
            'unmatched_sentences': self.unmatched_sentences,
            'match_rate': round(self.match_rate, 1),
            'rules_count': len(self.rules),
            'warnings': self.warnings,
            'errors': self.errors,
            'matched_entities': [
                {
                    'sentence': e.sentence,
                    'pattern': e.pattern_matched,
                    'rule_code': e.rule_code,
                    'parameters': e.parameters,
                    'confidence': e.confidence,
                }
                for e in self.matched_entities
            ],
        }