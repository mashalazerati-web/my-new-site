# ai_module/rules/context.py
"""
Context شیء — داده‌ای که هر قانون برای ارزیابی دریافت می‌کند
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set


@dataclass
class StaffInfo:
    """اطلاعات یک پرستار"""
    id: int
    name: str
    first_name: str = ''
    last_name: str = ''
    position: str = ''
    position_label: str = ''
    shift_type: str = 'سه_نوبتی'
    employment_status: str = 'رسمی'
    work_experience: int = 0
    legal_hours: float = 150.0
    max_hours: float = 230.0
    min_shifts: int = 15
    max_shifts: int = 23
    is_available: bool = True


@dataclass
class ScheduleContext:
    """Context مشترک برای ارزیابی همه قوانین."""
    
    ward_id: int
    ward_name: str
    year: int
    month: int
    days_in_month: int
    schedule_type: str = 'main'
    
    staff: Dict[int, StaffInfo] = field(default_factory=dict)
    schedule: Dict[int, Dict[int, str]] = field(default_factory=dict)
    requests: Dict[int, Dict[int, str]] = field(default_factory=dict)
    holidays: Set[int] = field(default_factory=set)
    weekend_days: Set[int] = field(default_factory=set)
    
    targets: Dict[str, int] = field(default_factory=lambda: {'M': 4, 'E': 4, 'N': 3})
    holiday_targets: Dict[str, int] = field(default_factory=lambda: {'M': 2, 'E': 2, 'N': 2})
    
    previous_month_last_day: Dict[int, str] = field(default_factory=dict)
    shift_codes: List[str] = field(default_factory=lambda: ['M', 'E', 'N', 'H', '-'])
    
    main_schedule: Dict[int, Dict[int, str]] = field(default_factory=dict)
    main_schedule_status: Optional[str] = None
    main_schedule_id: Optional[int] = None
    special_config: Optional[Dict[str, Any]] = None
    
    # برای ScheduleService
    fair_nights: Dict[int, float] = field(default_factory=dict)
    fair_shifts: Dict[int, float] = field(default_factory=dict)
    fair_weekends: Dict[int, float] = field(default_factory=dict)
    max_nights_per_staff: Optional[int] = None
    
    # ============================================
    # Helper Methods
    # ============================================
    
    def get_staff_schedule(self, staff_id: int) -> Dict[int, str]:
        return self.schedule.get(staff_id, {})
    
    def get_staff_shift(self, staff_id: int, day: int) -> str:
        return self.schedule.get(staff_id, {}).get(day, '')
    
    def get_main_schedule_shift(self, staff_id: int, day: int) -> str:
        return self.main_schedule.get(staff_id, {}).get(day, '')
    
    def get_daily_needs(self, day: int) -> Dict[str, int]:
        if self.is_holiday_or_weekend(day):
            return self.holiday_targets.copy()
        return self.targets.copy()
    
    # ============================================
    # ✅ find_staff_by_name — پشتیبانی از نام‌های چندکلمه‌ای
    # ============================================
    
    def find_staff_by_name(self, name: str) -> Optional[StaffInfo]:
        """
        پیدا کردن پرستار بر اساس نام.
        
        اولویت:
        1. نام کامل (first + last)
        2. نام‌خانوادگی (last_name)
        3. نام کوچک (first_name)
        4. نام کامل بدون فاصله
        5. substring در نام کامل
        6. اشتراک حداقل ۲ کلمه
        """
        if not name:
            return None
        
        name = name.strip()
        if not name:
            return None
        
        name_lower = name.lower()
        
        # ۱. تطابق کامل
        for staff in self.staff.values():
            full_name = f"{staff.first_name} {staff.last_name}".strip().lower()
            if full_name == name_lower:
                return staff
        
        # ۲. تطابق نام‌خانوادگی
        for staff in self.staff.values():
            if staff.last_name and staff.last_name.strip().lower() == name_lower:
                return staff
        
        # ۳. تطابق نام کوچک
        for staff in self.staff.values():
            if staff.first_name and staff.first_name.strip().lower() == name_lower:
                return staff
        
        # ۴. تطابق نام کامل بدون فاصله
        for staff in self.staff.values():
            full_name = f"{staff.first_name} {staff.last_name}".strip().lower()
            if name_lower.replace(' ', '') == full_name.replace(' ', ''):
                return staff
        
        # ۵. substring
        for staff in self.staff.values():
            full_name = f"{staff.first_name} {staff.last_name}".strip().lower()
            if name_lower in full_name or full_name in name_lower:
                return staff
        
        # ۶. اشتراک حداقل ۲ کلمه
        name_parts = set(name_lower.split())
        best_match = None
        best_common = 0
        
        for staff in self.staff.values():
            full_name = f"{staff.first_name} {staff.last_name}".strip().lower()
            full_parts = set(full_name.split())
            common = name_parts & full_parts
            
            if len(common) > best_common:
                best_common = len(common)
                best_match = staff
        
        if best_common >= 2:
            return best_match
        
        return None
    
    def get_staff_names(self) -> List[str]:
        return [s.name for s in self.staff.values()]
    
    def get_staff_id(self, name: str) -> Optional[int]:
        staff = self.find_staff_by_name(name)
        return staff.id if staff else None
    
    def get_consecutive_nights(self, staff_id: int, day: int) -> int:
        schedule = self.get_staff_schedule(staff_id)
        count = 0
        d = day
        while d >= 1:
            shift = schedule.get(d, '')
            if 'N' in shift:
                count += 1
                d -= 1
            else:
                break
        return count
    
    def get_consecutive_work_days(self, staff_id: int, day: int) -> int:
        schedule = self.get_staff_schedule(staff_id)
        count = 0
        d = day
        while d >= 1:
            shift = schedule.get(d, '')
            if shift and shift not in ('-', 'H', 'S', 'off'):
                count += 1
                d -= 1
            else:
                break
        return count
    
    def is_weekend(self, day: int) -> bool:
        return day in self.weekend_days
    
    def is_holiday(self, day: int) -> bool:
        return day in self.holidays
    
    def is_holiday_or_weekend(self, day: int) -> bool:
        return day in self.holidays or day in self.weekend_days
    
    def count_shift_in_month(self, staff_id: int, shift_types: List[str] = None) -> int:
        schedule = self.get_staff_schedule(staff_id)
        count = 0
        for day, shift in schedule.items():
            if not shift or shift in ('-', 'H', 'S', 'off'):
                continue
            if shift_types:
                if any(st in shift for st in shift_types):
                    count += 1
            else:
                count += 1
        return count
    
    def count_weekend_shifts(self, staff_id: int) -> int:
        schedule = self.get_staff_schedule(staff_id)
        count = 0
        for day, shift in schedule.items():
            if self.is_weekend(day) and shift and shift not in ('-', 'H', 'S', 'off'):
                count += 1
        return count
    
    def get_main_schedule_staff_ids(self) -> List[int]:
        return [staff_id for staff_id in self.main_schedule.keys()]
    
    def is_staff_in_main(self, staff_id: int) -> bool:
        return staff_id in self.main_schedule and bool(self.main_schedule[staff_id])