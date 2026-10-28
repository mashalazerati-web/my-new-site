# ai_module/prompt/patterns/staff_combination_pattern.py
"""
الگو: [نام] و [نام] ... [شیفت] باشند
"""

import re

from .base_pattern import BasePattern
from ..entities import ExtractedEntity


class StaffCombinationPattern(BasePattern):
    """
    الگو:
        "خانم رضایی و آقای احمدی صبح باشند"
        "رضایی، احمدی و سعیدی شب"
    """
    
    pattern_code = 'staff_combination'
    priority = 150
    SHIFT_MAP = {'صبح': 'M', 'عصر': 'E', 'شب': 'N'}
    
    regex = (
        r'^\s*'
        r'(?P<names>'
        r'(?:(?:خانم|آقای|جناب|سرکار)\s+)?[\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?'
        r'(?:\s*(?:,|،|\s+و\s+)\s*'
        r'(?:(?:خانم|آقای|جناب|سرکار)\s+)?[\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?'
        r')+'
        r')'
        r'\s+'
        r'(?P<shift>صبح|عصر|شب)'
        r'\s*'
        r'(?:باشند|کار\s*کنند|بگذارید)?'
        r'\s*$'
    )
    
    def extract(self, sentence, match, context):
        names_text = match.group('names').strip()
        
        names = re.split(r'\s*(?:,|،|\s+و\s+)\s*', names_text)
        names = [self._clean_name(n.strip()) for n in names if n.strip()]
        
        if len(names) < 2:
            return None
        
        staff_list = []
        for name in names:
            staff = context.find_staff_by_name(name)
            if staff:
                staff_list.append(staff)
        
        if len(staff_list) < 2:
            return None
        
        shift_word = match.group('shift')
        shift = self.SHIFT_MAP.get(shift_word)
        if not shift:
            return None
        
        return ExtractedEntity(
            sentence=sentence,
            pattern_matched=self.pattern_code,
            rule_code='preferred_shift_for_staff',
            parameters={
                'staff_ids': [s.id for s in staff_list],
                'staff_names': [s.name for s in staff_list],
                'preferred_shift': shift,
                'days': None,
                'mode': 'includes',
                'is_multi': True,
            },
            confidence=0.9,
        )
    
    def _clean_name(self, name: str) -> str:
        prefixes = ['خانم', 'آقای', 'جناب', 'سرکار']
        for prefix in prefixes:
            if name.startswith(prefix + ' '):
                name = name[len(prefix) + 1:]
        return name.strip()