# ai_module/prompt/normalizer.py
"""
نرمال‌سازی متن فارسی پرامپت
"""

import re
from typing import Dict


class PromptNormalizer:
    """
    نرمال‌ساز متن پرامپت فارسی.
    
    وظایف:
    - تبدیل اعداد فارسی/عربی به انگلیسی
    - نرمال‌سازی ی و ک عربی
    - حذف نیم‌فاصله اضافی
    - تبدیل نشانه‌های نگارشی عربی به فارسی
    - حذف فاصله‌های اضافی
    """
    
    # نگاشت اعداد فارسی
    PERSIAN_DIGITS = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
    }
    
    # نگاشت اعداد عربی
    ARABIC_DIGITS = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
    }
    
    # نگاشت کاراکترهای عربی به فارسی
    ARABIC_TO_PERSIAN = {
        'ي': 'ی',
        'ك': 'ک',
        'ﻻ': 'لا',
        'ﻷ': 'لأ',
        'ۀ': 'ه',
        'ة': 'ه',
    }
    
    # نگاشت نشانه‌های نگارشی عربی به فارسی
    PUNCTUATION_MAP = {
        '،': ',',   # ویرگول عربی → انگلیسی (برای تقسیم)
        '؛': ';',
        '؟': '?',
        '٪': '%',
    }
    
    # کاراکترهای اضافی برای حذف
    EXTRA_CHARS = [
        '\u200c',  # نیم‌فاصله (در مرحله اول نگه می‌داریم)
        '\u200f',  # RLM
        '\u200e',  # LRM
        '\u202a',  # LRE
        '\u202b',  # RLE
        '\u202c',  # PDF
        '\u202d',  # LRO
        '\u202e',  # RLO
    ]
    
    def normalize(self, text: str) -> str:
        """
        نرمال‌سازی کامل متن.
        
        Args:
            text: متن خام ورودی
        
        Returns:
            متن نرمال‌شده
        """
        if not text:
            return ''
        
        # ۱. تبدیل اعداد فارسی و عربی
        text = self._convert_digits(text)
        
        # ۲. تبدیل کاراکترهای عربی به فارسی
        text = self._convert_arabic_to_persian(text)
        
        # ۳. حذف کاراکترهای کنترلی
        text = self._remove_control_chars(text)
        
        # ۴. نرمال‌سازی فاصله‌ها
        text = self._normalize_whitespace(text)
        
        # ۵. نرمال‌سازی نشانه‌ها
        text = self._normalize_punctuation(text)
        
        return text.strip()
    
    def _convert_digits(self, text: str) -> str:
        """تبدیل اعداد فارسی/عربی به انگلیسی"""
        # اعداد فارسی
        for persian, english in self.PERSIAN_DIGITS.items():
            text = text.replace(persian, english)
        
        # اعداد عربی
        for arabic, english in self.ARABIC_DIGITS.items():
            text = text.replace(arabic, english)
        
        return text
    
    def _convert_arabic_to_persian(self, text: str) -> str:
        """تبدیل کاراکترهای عربی به فارسی"""
        for arabic, persian in self.ARABIC_TO_PERSIAN.items():
            text = text.replace(arabic, persian)
        return text
    
    def _remove_control_chars(self, text: str) -> str:
        """حذف کاراکترهای کنترلی"""
        for char in self.EXTRA_CHARS:
            text = text.replace(char, '')
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """
        نرمال‌سازی فاصله‌ها:
        - فاصله‌های چندگانه → یک فاصله
        - خطوط جدید متعدد → خط جدید
        """
        # تبدیل tab به فاصله
        text = text.replace('\t', ' ')
        
        # چند فاصله → یک فاصله
        text = re.sub(r' +', ' ', text)
        
        # چند خط جدید → یک خط
        text = re.sub(r'\n+', '\n', text)
        
        return text
    
    def _normalize_punctuation(self, text: str) -> str:
        """نرمال‌سازی نشانه‌ها"""
        for arabic, standard in self.PUNCTUATION_MAP.items():
            text = text.replace(arabic, standard)
        return text
    
    def extract_numbers(self, text: str) -> list:
        """استخراج اعداد از متن"""
        return [int(n) for n in re.findall(r'\d+', text)]
    
    def extract_names_candidates(self, text: str) -> list:
        """
        استخراج کاندیدهای نام (کلمات با حرف اول بزرگ یا بعد از عنوان).
        ساده — برای استخراج دقیق از Rule Engine استفاده می‌شود.
        """
        # الگوهای آقا/خانم/جناب
        titles = ['آقای', 'خانم', 'جناب', 'سرکار']
        names = []
        
        for title in titles:
            pattern = rf'{title}\s+([\u0600-\u06FF]+)'
            matches = re.findall(pattern, text)
            names.extend(matches)
        
        return names


# ============================================
# تست سریع
# ============================================
if __name__ == '__main__':
    normalizer = PromptNormalizer()
    
    tests = [
        "خانم رضایی از روز ۱۰ تا ۱۵ صبح باشد",
        "آقای احمدي فقط شب کار کند",
        "حداکثر ۲ شب متوالی",
        "خانم رضایی، آقای احمدی و خانم سعیدی صبح",
    ]
    
    for t in tests:
        result = normalizer.normalize(t)
        print(f"ورودی:  {t}")
        print(f"خروجی: {result}")
        print(f"اعداد: {normalizer.extract_numbers(result)}")
        print('-' * 60)