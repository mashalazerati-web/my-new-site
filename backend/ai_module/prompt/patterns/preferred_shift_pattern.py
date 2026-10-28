# ai_module/prompt/patterns/preferred_shift_pattern.py
"""
الگو: [نام] (از روز X تا Y) [شیفت] باشد
نسخه ۲.۰ — پشتیبانی از نام‌های چندکلمه‌ای
"""

import re

from .base_pattern import BasePattern
from ..entities import ExtractedEntity


class PreferredShiftPattern(BasePattern):
    """
    الگوهای پشتیبانی‌شده:
    
    1. "خانم رضایی صبح باشد"
    2. "خانم رضایی از روز 10 تا 15 صبح باشد"
    3. "خانم غیاثی نوش آبادی صبح باشد"           ← ✅ نام سه‌کلمه‌ای
    4. "آقای احمدی شب کار کند"
    5. "آقای احمدی از روز 10 تا 15 شب باشد"
    6. "طاهره زارع مقدم فینی شب باشد"            ← ✅ نام چهارکلمه‌ای
    """
    
    pattern_code = 'preferred_shift'
    priority = 100
    
    SHIFT_MAP = {'صبح': 'M', 'عصر': 'E', 'شب': 'N'}
    
    FORBIDDEN_IN_NAME = [
        'صبح', 'عصر', 'شب',
        'باشد', 'باشند', 'کار', 'کند', 'کنند', 'بکند',
        'از', 'تا', 'روز',
        'حداکثر', 'حداقل', 'بیشتر', 'کمتر',
        'همه', 'تمام', 'به', 'جز',
        'مرخصی', 'آف',
    ]
    
    def __init__(self):
        # ساخت regex به صورت داینامیک برای lookahead
        forbidden_pattern = '|'.join(self.FORBIDDEN_IN_NAME)
        
        self.regex = (
            r'^\s*'
            # ============================================
            # نام — چند کلمه، ولی بدون کلمات ممنوعه
            # ============================================
            r'(?P<name>'
            r'(?:(?:خانم|آقای|جناب|سرکار|مهندس|دکتر)\s+)?'
            r'(?:(?!' + forbidden_pattern + r')(?<![\u0600-\u06FF])[\u0600-\u06FF]+(?![\u0600-\u06FF])\s*)+'
            r')'
            r'\s+'
            # ============================================
            # بازه روز (اختیاری)
            # ============================================
            r'(?:'
            r'از\s+روز\s+(?P<start>\d+)\s+تا\s+(?:روز\s+)?(?P<end>\d+)'
            r'|'
            r'روز\s+(?P<single_day>\d+)'
            r')?'
            r'\s*'
            # ============================================
            # شیفت (اجباری)
            # ============================================
            r'(?P<shift>صبح|عصر|شب)'
            r'\s*'
            # ============================================
            # فعل (اختیاری)
            # ============================================
            r'(?:باشد|باشند|کار\s*کند|کار\s*کنند|بگذاری|بگذارید|بکن|بکند)?'
            r'\s*$'
        )
        
        super().__init__()
    
    def extract(self, sentence, match, context):
        name = match.group('name').strip()
        name = self._clean_name(name)
        
        if not name:
            return None
        
        # چک نهایی: نام نباید شامل کلمات ممنوعه باشد
        for forbidden in self.FORBIDDEN_IN_NAME:
            # استفاده از word boundary
            if re.search(r'\b' + re.escape(forbidden) + r'\b', name):
                return None
        
        staff = context.find_staff_by_name(name)
        if not staff:
            return None
        
        shift_word = match.group('shift')
        shift = self.SHIFT_MAP.get(shift_word)
        if not shift:
            return None
        
        days = None
        start = match.group('start')
        end = match.group('end')
        single = match.group('single_day')
        
        if start and end:
            days = list(range(int(start), int(end) + 1))
        elif single:
            days = [int(single)]
        
        return ExtractedEntity(
            sentence=sentence,
            pattern_matched=self.pattern_code,
            rule_code='preferred_shift_for_staff',
            parameters={
                'staff_id': staff.id,
                'staff_name': staff.name,
                'preferred_shift': shift,
                'days': days,
                'mode': 'includes',
            },
            confidence=1.0 if days is None else 0.95,
        )
    
    def _clean_name(self, name: str) -> str:
        prefixes = ['خانم', 'آقای', 'جناب', 'سرکار', 'مهندس', 'دکتر']
        for prefix in prefixes:
            if name.startswith(prefix + ' '):
                name = name[len(prefix) + 1:]
        return name.strip()