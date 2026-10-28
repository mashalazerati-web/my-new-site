# ai_module/prompt/patterns/constraint_pattern.py
"""
الگو: محدودیت‌ها (حداکثر/حداقل)
"""

import re

from .base_pattern import BasePattern
from ..entities import ExtractedEntity


class ConstraintPattern(BasePattern):
    """
    الگو:
        "حداکثر 2 شب متوالی"
        "حداقل 3 شیفت"
    """
    
    pattern_code = 'constraint'
    priority = 70
    
    # regex عمومی — فقط چک می‌کند که "حداکثر" یا "حداقل" هست
    regex = r'^\s*(?:حداکثر|حداقل|بیشتر\s+از|کمتر\s+از).+$'
    
    # الگوهای اختصاصی برای استخراج
    SPECIFIC_PATTERNS = [
        (
            r'حداکثر\s+(\d+)\s+شب\s+متوالی',
            'max_consecutive_nights',
            lambda v: {'max_nights': v},
        ),
        (
            r'حداکثر\s+(\d+)\s+شیفت',
            'fair_shift_distribution',
            lambda v: {'max_shift_per_staff': v},
        ),
        (
            r'حداقل\s+(\d+)\s+شیفت',
            'fair_shift_distribution',
            lambda v: {'min_shift_per_staff': v},
        ),
    ]
    
    def extract(self, sentence, match, context):
        for pattern, rule_code, param_builder in self.SPECIFIC_PATTERNS:
            m = re.search(pattern, sentence)
            if m:
                value = int(m.group(1))
                params = param_builder(value)
                
                return ExtractedEntity(
                    sentence=sentence,
                    pattern_matched=self.pattern_code,
                    rule_code=rule_code,
                    parameters=params,
                    confidence=0.9,
                )
        
        return None