# ai_module/prompt/patterns/all_staff_pattern.py
"""
الگو: همه [شیفت] باشند (به جز [نام])
"""

import re

from .base_pattern import BasePattern
from ..entities import ExtractedEntity


class AllStaffPattern(BasePattern):
    """
    الگو:
        "همه صبح باشند"
        "همه کارکنان شب کار کنند به جز آقای احمدی"
    """
    
    pattern_code = 'all_staff'
    priority = 200
    SHIFT_MAP = {'صبح': 'M', 'عصر': 'E', 'شب': 'N'}
    
    regex = (
        r'^\s*'
        r'(?:همه|تمام|کل|تمام\s+کارکنان|همه\s+کارکنان|همه\s+پرستاران|کارکنان|پرستاران)'
        r'\s+'
        r'(?P<shift>صبح|عصر|شب)'
        r'\s*'
        r'(?:باشند|کار\s*کنند|بگذارید)?'
        r'(?:\s+به\s+جز\s+'
        r'(?:(?:خانم|آقای|جناب|سرکار)\s+)?'
        r'(?P<exclude>[\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)'
        r')?'
        r'\s*$'
    )
    
    def extract(self, sentence, match, context):
        shift_word = match.group('shift')
        shift = self.SHIFT_MAP.get(shift_word)
        
        if not shift:
            return None
        
        exclude_name = match.group('exclude')
        exclude_staff_id = None
        exclude_staff_name = None
        
        if exclude_name:
            exclude_name = self._clean_name(exclude_name.strip())
            staff = context.find_staff_by_name(exclude_name)
            if staff:
                exclude_staff_id = staff.id
                exclude_staff_name = staff.name
        
        return ExtractedEntity(
            sentence=sentence,
            pattern_matched=self.pattern_code,
            rule_code='preferred_shift_for_staff',
            parameters={
                'staff_id': None,
                'staff_name': None,
                'preferred_shift': shift,
                'is_all_staff': True,
                'exclude_staff_id': exclude_staff_id,
                'exclude_staff_name': exclude_staff_name,
            },
            confidence=0.85,
        )
    
    def _clean_name(self, name: str) -> str:
        prefixes = ['خانم', 'آقای', 'جناب', 'سرکار']
        for prefix in prefixes:
            if name.startswith(prefix + ' '):
                name = name[len(prefix) + 1:]
        return name.strip()