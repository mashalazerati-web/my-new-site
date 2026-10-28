# ai_module/prompt/interpreter.py
"""
مفسر پرامپت — قلب سیستم
"""

import time
from typing import List, Optional

from .normalizer import PromptNormalizer
from .tokenizer import PromptTokenizer
from .entities import (
    PromptInterpretationResult,
    ExtractedEntity,
)
from ..rules.context import ScheduleContext
from ..rules.registry import RuleRegistry, get_rule_registry


class PromptInterpreter:
    """
    مفسر پرامپت فارسی.
    """
    
    def __init__(
        self,
        context: ScheduleContext,
        registry: Optional[RuleRegistry] = None,
    ):
        self.context = context
        self.registry = registry or get_rule_registry()
        self.normalizer = PromptNormalizer()
        self.tokenizer = PromptTokenizer()
        
        # ⭐ ترتیب مهم: از خاص‌ترین به عمومی‌ترین
        # import محلی برای جلوگیری از circular import
        from .patterns import (
            AllStaffPattern,
            StaffCombinationPattern,
            PreferredShiftPattern,
            DateRangePattern,
            ConstraintPattern,
            CoveragePattern,
        )
        
        self.patterns = [
            AllStaffPattern(),            # priority=200
            StaffCombinationPattern(),    # priority=150
            PreferredShiftPattern(),      # priority=100
            DateRangePattern(),           # priority=90
            ConstraintPattern(),          # priority=70
            CoveragePattern(),            # priority=60
        ]
        # مرتب‌سازی نزولی بر اساس priority
        self.patterns.sort(key=lambda p: p.priority, reverse=True)
    
    def interpret(self, prompt: str) -> PromptInterpretationResult:
        """تفسیر کامل پرامپت"""
        start_time = time.time()
        
        result = PromptInterpretationResult(original_prompt=prompt)
        
        if not prompt or not prompt.strip():
            return result
        
        # ۱. نرمال‌سازی
        normalized = self.normalizer.normalize(prompt)
        result.normalized_prompt = normalized
        
        # ۲. تقسیم
        sentences = self.tokenizer.tokenize(normalized)
        result.sentences = sentences
        
        if not sentences:
            return result
        
        # ۳. تطبیق الگوها
        for sentence in sentences:
            entity = self._match_sentence(sentence)
            if entity:
                result.matched_entities.append(entity)
            else:
                result.unmatched_sentences.append(sentence)
        
        # ۴. ساخت قوانین
        for entity in result.matched_entities:
            rules = self._build_rules(entity)
            result.rules.extend(rules)
        
        return result
    
    def _match_sentence(self, sentence: str) -> Optional[ExtractedEntity]:
        """تلاش برای تطبیق یک جمله با الگوها"""
        for pattern in self.patterns:
            match = pattern.match(sentence)
            if match:
                entity = pattern.extract(sentence, match, self.context)
                if entity:
                    return entity
        return None
    
    def _build_rules(self, entity: ExtractedEntity) -> List:
        """ساخت قوانین از یک موجودیت"""
        rules = []
        
        try:
            if entity.rule_code == 'preferred_shift_for_staff':
                rules.extend(self._build_preferred_shift_rules(entity))
            elif entity.rule_code == 'max_consecutive_nights':
                rules.extend(self._build_max_consecutive_rules(entity))
            elif entity.rule_code == 'fair_shift_distribution':
                rules.append(self.registry.create(
                    'fair_shift_distribution',
                    **entity.parameters,
                ))
            else:
                # عمومی
                rule = self.registry.create(
                    entity.rule_code,
                    **entity.parameters,
                )
                rules.append(rule)
        except Exception as e:
            print(f"⚠️ خطا در ساخت قانون: {e}")
            import traceback
            traceback.print_exc()
        
        return rules
    
    def _build_preferred_shift_rules(self, entity) -> List:
        """ساخت قوانین PreferredShift"""
        rules = []
        params = entity.parameters
        
        # حالت همه پرستاران
        if params.get('is_all_staff'):
            exclude_id = params.get('exclude_staff_id')
            for staff_id, staff in self.context.staff.items():
                if exclude_id and staff_id == exclude_id:
                    continue
                rules.append(self.registry.create(
                    'preferred_shift_for_staff',
                    staff_id=staff_id,
                    preferred_shift=params['preferred_shift'],
                    days=params.get('days'),
                    mode=params.get('mode', 'includes'),
                    staff_name=staff.name,
                ))
            return rules
        
        # حالت چند پرستار
        if params.get('is_multi'):
            for staff_id, staff_name in zip(
                params.get('staff_ids', []),
                params.get('staff_names', [])
            ):
                rules.append(self.registry.create(
                    'preferred_shift_for_staff',
                    staff_id=staff_id,
                    preferred_shift=params['preferred_shift'],
                    days=params.get('days'),
                    mode=params.get('mode', 'includes'),
                    staff_name=staff_name,
                ))
            return rules
        
        # تک پرستار
        if params.get('staff_id'):
            rules.append(self.registry.create(
                'preferred_shift_for_staff',
                staff_id=params['staff_id'],
                preferred_shift=params['preferred_shift'],
                days=params.get('days'),
                mode=params.get('mode', 'includes'),
                staff_name=params.get('staff_name'),
            ))
        
        return rules
    
    def _build_max_consecutive_rules(self, entity) -> List:
        """ساخت قانون حداکثر شب متوالی"""
        params = entity.parameters
        if params.get('max_nights'):
            return [self.registry.create(
                'max_consecutive_nights',
                max_nights=params['max_nights'],
            )]
        return []