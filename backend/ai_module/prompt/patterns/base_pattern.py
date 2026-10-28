# ai_module/prompt/patterns/base_pattern.py
"""
کلاس پایه برای الگوهای regex
"""

from abc import ABC, abstractmethod
import re
from typing import Optional

from ...rules.context import ScheduleContext
from ..entities import ExtractedEntity


class BasePattern(ABC):
    """
    کلاس پایه همه الگوها.
    """
    
    pattern_code: str = 'base_pattern'
    priority: int = 100
    regex: str = ''
    
    def __init__(self):
        # ✅ استفاده از re.VERBOSE + re.UNICODE + re.IGNORECASE
        # بدون re.VERBOSE، # به عنوان کامنت شناخته نمی‌شود
        self._compiled = re.compile(
            self.regex,
            re.VERBOSE | re.UNICODE | re.IGNORECASE | re.MULTILINE
        )
    
    def match(self, sentence: str) -> Optional[re.Match]:
        """آیا این الگو تطبیق می‌کند؟"""
        if not sentence:
            return None
        return self._compiled.search(sentence.strip())
    
    @abstractmethod
    def extract(
        self,
        sentence: str,
        match: re.Match,
        context: ScheduleContext,
    ) -> Optional[ExtractedEntity]:
        """استخراج موجودیت از تطبیق"""
        pass
    
    def __repr__(self):
        return f"<{self.__class__.__name__} code={self.pattern_code} priority={self.priority}>"