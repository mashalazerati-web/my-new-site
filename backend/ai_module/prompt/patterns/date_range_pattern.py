# ai_module/prompt/patterns/date_range_pattern.py
"""
الگو: [نام] از روز X تا Y مرخصی است
"""

import re

from .base_pattern import BasePattern
from ..entities import ExtractedEntity


class DateRangePattern(BasePattern):
    """
    الگو: [نام] (از) (روز|تاریخ) X تا (روز|تاریخ) Y [عمل]
    """
    
    pattern_code = 'date_range'
    priority = 90
    
    # ✅ رویکرد جدید: کل regex را ساده می‌کنیم و استخراج دقیق‌تر
    regex = (
        r'^\s*'
        # بخش اول: نام (بدون «از» و «روز» و...)
        r'(?P<name>'
        r'(?:(?:خانم|آقای|جناب|سرکار)\s+)?'
        r'[\u0600-\u06FF]+'
        r'(?:\s+[\u0600-\u06FF]+)?'
        r')'
        r'\s+'
        r'(?:از\s+)?'
        r'(?:روز|تاریخ)\s+'
        r'(?P<start>\d+)'
        r'\s+تا\s+'
        r'(?:(?:روز|تاریخ)\s+)?'
        r'(?P<end>\d+)'
        r'\s+'
        r'(?P<action>مرخصی|آف|در\s*دسترس\s*نباشد|نباشد|استراحت)'
        r'(?:\s+است|\s+باشد|\s+هستند)?'
        r'\s*$'
    )
    
    # کلمات ممنوعه برای نام
    FORBIDDEN_IN_NAME = ['از', 'تا', 'روز', 'تاریخ', 'مرخصی', 'آف']
    
    def extract(self, sentence, match, context):
        name = match.group('name').strip()
        name = self._clean_name(name)
        
        if not name:
            return None
        
        # ✅ اگر نام بیش از حد طولانی است، بخش اول را جدا کن
        # مثال: "سعیدی از" → "سعیدی"
        name = self._truncate_at_forbidden(name)
        
        if not name:
            return None
        
        staff = context.find_staff_by_name(name)
        if not staff:
            return None
        
        start = int(match.group('start'))
        end = int(match.group('end'))
        
        if start > end or start < 1:
            return None
        
        days = list(range(start, end + 1))
        
        return ExtractedEntity(
            sentence=sentence,
            pattern_matched=self.pattern_code,
            rule_code='preferred_shift_for_staff',
            parameters={
                'staff_id': staff.id,
                'staff_name': staff.name,
                'preferred_shift': '-',
                'days': days,
                'mode': 'exact',
            },
            confidence=0.95,
        )
    
    def _clean_name(self, name: str) -> str:
        """حذف پیشوندهای عنوان"""
        prefixes = ['خانم', 'آقای', 'جناب', 'سرکار']
        for prefix in prefixes:
            if name.startswith(prefix + ' '):
                name = name[len(prefix) + 1:]
        return name.strip()
    
    def _truncate_at_forbidden(self, name: str) -> str:
        """
        اگر نام شامل کلمات ممنوعه است، در آن نقطه قطع کن.
        مثال: "سعیدی از" → "سعیدی"
        """
        words = name.split()
        clean_words = []
        
        for word in words:
            if word in self.FORBIDDEN_IN_NAME:
                break
            clean_words.append(word)
        
        return ' '.join(clean_words).strip()