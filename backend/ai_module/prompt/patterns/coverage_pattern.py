# ai_module/prompt/patterns/coverage_pattern.py
"""
الگو: افزایش/کاهش پرسنل در روز X
"""

import re

from .base_pattern import BasePattern
from ..entities import ExtractedEntity


class CoveragePattern(BasePattern):
    """
    الگو:
        "روز 10 یک نفر اضافه صبح نیاز داریم"
        "روز 15 کمبود عصر داریم"
    """
    
    pattern_code = 'coverage'
    priority = 60
    SHIFT_MAP = {'صبح': 'M', 'عصر': 'E', 'شب': 'N'}
    
    regex = (
        r'^\s*'
        r'روز\s+(?P<day>\d+)'
        r'\s+'
        r'(?P<action>اضافه|کمبود|افزایش|کاهش)'
        r'\s+'
        r'(?:یک\s+نفر\s+)?'
        r'(?P<shift>صبح|عصر|شب)'
        r'.*$'
    )
    
    def extract(self, sentence, match, context):
        day = int(match.group('day'))
        if day < 1 or day > context.days_in_month:
            return None
        
        action = match.group('action')
        shift_word = match.group('shift')
        shift = self.SHIFT_MAP.get(shift_word)
        
        if not shift:
            return None
        
        direction = 'increase' if action in ('اضافه', 'افزایش') else 'decrease'
        count = 1 if direction == 'increase' else -1
        
        return ExtractedEntity(
            sentence=sentence,
            pattern_matched=self.pattern_code,
            rule_code='coverage_adjustment',
            parameters={
                'day': day,
                'shift': shift,
                'count': count,
                'direction': direction,
            },
            confidence=0.85,
        )