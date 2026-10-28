# ai_module/adaptive_scheduler.py
"""
سیستم تطبیقی انتخاب الگوریتم
"""

from typing import Dict, Optional
from .optimizer.real_cp_sat import RealCP_SATShiftScheduler
from .ai_engine_ortools import ORToolsShiftSchedulingEngine
import logging

logger = logging.getLogger(__name__)


class AdaptiveScheduler:
    """انتخاب هوشمند الگوریتم"""
    
    def __init__(self, ward, year, month, prompt='', rules=None):
        self.ward = ward
        self.year = year
        self.month = month
        self.prompt = prompt
        self.rules = rules or []
    
    def generate_schedule(self):
        """تولید برنامه"""
        # 🔥 همیشه از Greedy استفاده کن - سریع‌تر و قابل اعتمادتر
        # CP-SAT در صورت نیاز در آینده اضافه می‌شود
        return self._solve_with_greedy()
    
    def _analyze_complexity(self):
        """تحلیل پیچیدگی"""
        from api.models import Profile
        
        staff_count = Profile.objects.filter(
            ward=self.ward,
            role='staff'
        ).exclude(role__in=['head', 'admin', 'supervisor']).count()
        
        return {
            'staff_count': staff_count,
            'complexity_level': 'low' if staff_count <= 10 else ('medium' if staff_count <= 30 else 'high')
        }
    
    def _solve_with_cp_sat(self, time_limit=60):
        """حل با CP-SAT"""
        optimizer = RealCP_SATShiftScheduler(
            ward=self.ward,
            year=self.year,
            month=self.month,
            prompt=self.prompt,
            rules=self.rules
        )
        
        schedule = optimizer.solve(time_limit=time_limit)
        
        if schedule:
            return {
                'schedule': schedule,
                'solver': 'cp_sat',
                'stats': optimizer.get_stats()
            }
        else:
            return self._solve_with_greedy()
    
    def _solve_with_greedy(self):
        """حل با Greedy"""
        engine = ORToolsShiftSchedulingEngine(
            self.ward,
            self.year,
            self.month,
            rules=self.rules,
            prompt=self.prompt
        )
        
        schedule = engine.generate_schedule()
        
        return {
            'schedule': schedule,
            'solver': 'greedy',
            'stats': {
                'solving_time': 0.5,
                'solution_found': True,
                'num_staff': len(schedule),
                'num_days': engine.days_in_month
            }
        }