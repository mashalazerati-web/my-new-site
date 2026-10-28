# ai_module/prompt/tokenizer.py
"""
تقسیم پرامپت به جملات معنادار
"""

import re
from typing import List


class PromptTokenizer:
    """
    تقسیم متن به جملات.
    
    الگوریتم:
    1. Pre-scan: تشخیص اگر متن «لیست اسم‌ها + فعل مشترک» است
    2. اگر لیست است → فقط بر نقطه و ; و خط جدید تقسیم کن
    3. اگر ترکیبی است → بر ویرگول و «و» هم تقسیم کن
    """
    
    # جداکننده‌های قطعی (همیشه اعمال می‌شوند)
    HARD_SEPARATORS = [
        r'\.\s+',       # نقطه + فاصله
        r';\s*',        # نقطه‌ویرگول
        r'\n+',         # خط جدید
    ]
    
    # جداکننده‌های نرم (فقط در جملات ترکیبی)
    SOFT_SEPARATORS = [
        r'،\s*',        # ویرگول فارسی
        r',\s*',        # ویرگول انگلیسی
    ]
    
    # افعال کامل
    COMPLETE_VERBS = [
        'باشد', 'باشند',
        'کار کند', 'کار کنند',
        'بگذاری', 'بگذارید',
        'بکند', 'بکنند',
        'داشته باشد', 'داشته باشند',
        'مرخصی است', 'مرخصی هستند',
        'آف باشد', 'آف باشند',
    ]
    
    def tokenize(self, text: str) -> List[str]:
        """تقسیم متن به جملات"""
        if not text:
            return []
        
        # ⭐ گام ۱: Pre-scan
        is_list = self._is_list_sentence(text)
        
        # گام ۲: تقسیم بر اساس جداکننده‌های قطعی
        sentences = [text]
        for sep in self.HARD_SEPARATORS:
            new_sentences = []
            for s in sentences:
                parts = re.split(sep, s)
                new_sentences.extend(parts)
            sentences = new_sentences
        
        # ⭐ گام ۳: اگر لیست نبود، تقسیم نرم هم انجام بده
        if not is_list:
            # ویرگول‌ها را جدا کن
            new_sentences = []
            for s in sentences:
                parts = re.split(r'[،,]', s)
                new_sentences.extend(parts)
            sentences = new_sentences
            
            # سپس «و» را جدا کن (با چک محتاطانه)
            sentences = self._split_conjunctions_safely(sentences)
        
        # گام ۴: پاکسازی
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _is_list_sentence(self, text: str) -> bool:
        """
        آیا این متن یک جمله «لیست اسم‌ها + فعل مشترک» است؟
        
        مثال TRUE:
            "خانم رضایی، آقای احمدی و خانم سعیدی شب باشند"
            → یک جمله با فاعل مرکب
        
        مثال FALSE:
            "خانم رضایی صبح باشد و آقای احمدی شب باشد"
            → دو جمله مستقل
        """
        # ۱. تعداد جداکننده‌ها (ویرگول + «و»)
        # ویرگول‌های فارسی و انگلیسی
        comma_count = len(re.findall(r'[،,]', text))
        # «و» که بین دو کلمه است
        vav_count = len(re.findall(r'\s+و\s+', text))
        total_separators = comma_count + vav_count
        
        if total_separators == 0:
            return False
        
        # ۲. تعداد افعال کامل
        verb_count = 0
        for verb in self.COMPLETE_VERBS:
            # \b برای مرز کلمه
            pattern = r'(?:^|\s)' + re.escape(verb) + r'(?:\s|$)'
            verb_count += len(re.findall(pattern, text))
        
        # ۳. اگر تعداد افعال مساوی تعداد جداکننده‌ها یا بیشتر → ترکیبی
        if verb_count >= total_separators:
            return False
        
        # ۴. اگر تعداد افعال ۱ و تعداد جداکننده‌ها ≥ ۱ → لیست
        if verb_count == 1 and total_separators >= 1:
            # ⚠️ چک اضافی: شاید بخش اول یک جمله کامل باشد ولی «و» جمله جدید شروع کند
            # مثال: "خانم رضایی صبح باشد و آقای احمدی شب" — این ترکیبی است
            # تشخیص: اگر بعد از جداکننده اول فعل باشد، ترکیبی است
            
            # تقسیم روی جداکننده اول
            first_sep_match = re.search(r'[،,]|\s+و\s+', text)
            if first_sep_match:
                first_part = text[:first_sep_match.start()]
                rest = text[first_sep_match.end():]
                
                # آیا بخش اول فعل کامل دارد؟
                first_has_verb = any(
                    re.search(r'(?:^|\s)' + re.escape(v) + r'(?:\s|$)', first_part)
                    for v in self.COMPLETE_VERBS
                )
                
                # اگر بخش اول فعل دارد → ترکیبی است
                if first_has_verb:
                    return False
            
            return True
        
        # ۵. تعداد افعال صفر → لیست ناقص
        if verb_count == 0:
            return False
        
        # پیش‌فرض: ترکیبی
        return False
    
    def _split_conjunctions_safely(self, sentences: List[str]) -> List[str]:
        """تقسیم محتاطانه بر «و»"""
        result = []
        
        for sentence in sentences:
            if ' و ' not in sentence:
                result.append(sentence)
                continue
            
            parts = re.split(r'\s+و\s+', sentence)
            
            if self._is_compound_sentence(parts):
                result.extend(parts)
            else:
                result.append(sentence)
        
        return result
    
    def _is_compound_sentence(self, parts: List[str]) -> bool:
        """آیا این «و» یک جمله را به دو جمله تبدیل می‌کند؟"""
        if len(parts) < 2:
            return False
        
        # هر قسمت باید فعل کامل داشته باشد (به‌جز آخرین)
        parts_with_verb = []
        for i, part in enumerate(parts):
            if self._has_complete_verb(part):
                parts_with_verb.append(i)
        
        # اگر همه قسمت‌ها فعل دارند → ترکیبی
        if len(parts_with_verb) == len(parts):
            return True
        
        # اگر فقط آخرین قسمت فعل دارد → لیست (یک جمله)
        if parts_with_verb == [len(parts) - 1]:
            return False
        
        # اگر فقط اولین قسمت فعل دارد → احتمالاً ترکیبی (با فعل حذف‌شده در دوم)
        if parts_with_verb == [0]:
            return True
        
        # اگر بیش از نصف قسمت‌ها فعل دارند → ترکیبی
        if len(parts_with_verb) > len(parts) / 2:
            return True
        
        return False
    
    def _has_complete_verb(self, text: str) -> bool:
        """آیا این متن شامل یک فعل کامل است؟"""
        for verb in self.COMPLETE_VERBS:
            pattern = r'(?:^|\s)' + re.escape(verb) + r'(?:\s|$)'
            if re.search(pattern, text):
                return True
        return False
    
    def classify_sentence(self, sentence: str) -> str:
        """تشخیص نوع جمله"""
        keywords = {
            'preferred_shift': ['صبح', 'عصر', 'شب'],
            'date_range': ['از روز', 'تا روز', 'از تاریخ', 'مرخصی'],
            'coverage': ['کمبود', 'اضافه', 'افزایش', 'کاهش'],
            'constraint': ['حداکثر', 'حداقل', 'بیشتر', 'کمتر'],
            'holiday': ['تعطیل', 'آف'],
        }
        
        for kind, words in keywords.items():
            if any(w in sentence for w in words):
                return kind
        
        return 'unknown'


# ============================================
# تست
# ============================================
if __name__ == '__main__':
    tokenizer = PromptTokenizer()
    
    tests = [
        ("خانم رضایی صبح باشد", 1),
        ("خانم رضایی صبح باشد و آقای احمدی شب باشد", 2),
        ("خانم رضایی و آقای احمدی صبح باشند", 1),
        ("حداکثر 2 شب متوالی، روز 10 تعطیل باشد", 2),
        ("خانم رضایی، آقای احمدی و خانم سعیدی شب باشند", 1),
        ("آقای احمدی از روز 10 تا 15 شب باشد", 1),
        ("خانم سعیدی از روز 5 تا 10 مرخصی است", 1),
        ("خانم رضایی صبح باشد، آقای احمدی شب باشد، حداکثر 2 شب متوالی", 3),
    ]
    
    print("=" * 70)
    print("🧪 تست Tokenizer")
    print("=" * 70)
    
    all_passed = True
    
    for input_text, expected_count in tests:
        result = tokenizer.tokenize(input_text)
        passed = len(result) == expected_count
        
        if not passed:
            all_passed = False
        
        status = "✅" if passed else "❌"
        print(f"\n{status} ورودی: {input_text}")
        print(f"   جملات ({len(result)}) — انتظار: {expected_count}")
        for i, s in enumerate(result, 1):
            kind = tokenizer.classify_sentence(s)
            print(f"     {i}. [{kind}] {s}")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 همه تست‌های Tokenizer PASSED!")
    else:
        print("⚠️ بعضی تست‌ها FAILED")
    print("=" * 70)