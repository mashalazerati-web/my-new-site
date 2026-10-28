# ai_module/optimizer/real_cp_sat.py
"""
بهینه‌ساز برنامه شیفت با استفاده از OR-Tools CP-SAT
نسخه ۱.۰ - قابل استفاده برای هر بخش و هر ماه
"""

from ortools.sat.python import cp_model
from typing import Dict, List, Optional
import time
import logging
from collections import defaultdict
import jdatetime

logger = logging.getLogger(__name__)


class RealCP_SATShiftScheduler:
    """موتور برنامه‌ریزی شیفت با CP-SAT"""
    
    def __init__(self, ward, year, month, prompt='', rules=None):
        self.ward = ward
        self.year = year
        self.month = month
        self.prompt = prompt
        self.rules = rules or []
        
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.solving_time = 0
        self.solution_found = False
        
        self.num_days = self._get_days_in_month()
        self.num_staff = 0
        self.staff_data = []
        self.shift_types = []
        self.shift_durations = {}
        self.holidays = {}
        self.weekend_days = []
        self.staff_requests = {}
        
        self.shift_assignments = {}
        self.staff_hours = {}
        self.staff_night_counts = {}
        
    def _get_days_in_month(self):
        """تعداد روزهای ماه شمسی"""
        days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
        return days_in_month[self.month - 1]
    
    def _load_data(self):
        """بارگذاری داده‌های لازم"""
        from api.models import Profile, ShiftCode, Holiday, ShiftRequest
        
        # بارگذاری پرستاران
        profiles = Profile.objects.filter(
            ward=self.ward,
            role='staff'
        ).exclude(role__in=['head', 'admin', 'supervisor']).select_related('user')
        
        self.staff_data = []
        for profile in profiles:
            staff_info = {
                'id': profile.user.id,
                'name': f"{profile.user.first_name} {profile.user.last_name}",
                'shift_type': profile.shift_type or 'سه_نوبتی',
                'work_experience': profile.work_experience or 0,
                'employment_status': profile.employment_status or 'رسمی',
                'allowed_shifts': self._get_allowed_shifts(profile.shift_type),
                'max_hours': self._calculate_max_hours(profile)
            }
            self.staff_data.append(staff_info)
        
        self.num_staff = len(self.staff_data)
        
        # بارگذاری کدهای شیفت
        shift_codes = ShiftCode.objects.filter(
            ward=self.ward,
            is_active=True
        )
        
        self.shift_types = []
        self.shift_durations = {}
        for shift_code in shift_codes:
            self.shift_types.append(shift_code.code)
            self.shift_durations[shift_code.code] = self._get_shift_duration(shift_code.code)
        
        if not self.shift_types:
            self.shift_types = ['M', 'E', 'N', '-', 'H']
            self.shift_durations = {
                'M': 7.5, 'E': 7.5, 'N': 12, '-': 0, 'H': 0
            }
        
        # بارگذاری تعطیلات
        month_prefix = f"{self.year}-{str(self.month).zfill(2)}"
        holidays = Holiday.objects.filter(date__startswith=month_prefix)
        self.holidays = {int(h.date.split('-')[2]): h.name for h in holidays}
        
        # محاسبه روزهای تعطیل (جمعه‌ها)
        self.weekend_days = []
        for day in range(1, self.num_days + 1):
            try:
                date = jdatetime.date(self.year, self.month, day)
                if date.weekday() == 6:  # جمعه
                    self.weekend_days.append(day)
            except:
                pass
        
        # بارگذاری درخواست‌های شخصی
        requests = ShiftRequest.objects.filter(
            ward=self.ward,
            request_date__startswith=month_prefix,
            is_approved=True
        )
        
        self.staff_requests = defaultdict(dict)
        for req in requests:
            day = int(req.request_date.split('-')[2])
            staff_id = req.user.id
            if req.shift_code:
                self.staff_requests[staff_id][day] = req.shift_code.code
            else:
                self.staff_requests[staff_id][day] = 'off'
    
    def _get_allowed_shifts(self, shift_type):
        """تعیین شیفت‌های مجاز"""
        allowed = {
            'سه_نوبتی': ['M', 'E', 'N', 'ME', 'MN', 'EN', 'MEN', '-', 'H'],
            'ثابت_صبح': ['M', '-', 'H'],
            'ثابت_عصر': ['E', '-', 'H'],
            'ثابت_شب': ['N', '-', 'H'],
            'دو_نوبتی_عصر_شب': ['E', 'N', 'EN', '-', 'H'],
            'دو_نوبتی_صبح_شب': ['M', 'N', 'MN', '-', 'H'],
            'دو_نوبتی_صبح_عصر': ['M', 'E', 'ME', '-', 'H'],
            None: ['M', 'E', 'N', '-', 'H']
        }
        return allowed.get(shift_type, ['M', 'E', 'N', '-', 'H'])
    
    def _get_shift_duration(self, code):
        """مدت زمان هر شیفت"""
        durations = {
            'M': 7.5, 'E': 7.5, 'N': 12,
            'ME': 15, 'MN': 19.5, 'EN': 19.5, 'MEN': 27,
            '-': 0, 'H': 0
        }
        return durations.get(code, 7.5)
    
    def _calculate_max_hours(self, profile):
        """حداکثر ساعات کاری ماهانه"""
        base_hours = 38 * 4.33
        
        if profile.work_experience:
            if profile.work_experience > 16:
                base_hours -= 5 * 4.33
            elif profile.work_experience >= 12:
                base_hours -= 4 * 4.33
            elif profile.work_experience >= 8:
                base_hours -= 3 * 4.33
            elif profile.work_experience >= 4:
                base_hours -= 2 * 4.33
            else:
                base_hours -= 1 * 4.33
        
        if profile.shift_type == 'سه_نوبتی':
            base_hours -= 1 * 4.33
        
        return max(base_hours, 120)
    
    def _define_variables(self):
        """تعریف متغیرها"""
        for staff in self.staff_data:
            staff_id = staff['id']
            
            for day in range(1, self.num_days + 1):
                for shift_code in staff['allowed_shifts']:
                    var_name = f"staff_{staff_id}_day_{day}_shift_{shift_code}"
                    self.shift_assignments[(staff_id, day, shift_code)] = self.model.NewBoolVar(var_name)
            
            self.staff_hours[staff_id] = self.model.NewIntVar(
                0, int(staff['max_hours'] * 2), f"hours_{staff_id}"
            )
            
            self.staff_night_counts[staff_id] = self.model.NewIntVar(
                0, self.num_days, f"nights_{staff_id}"
            )
    
    def _add_constraints(self):
        """افزودن محدودیت‌ها"""
        # ۱. هر کارمند حداکثر یک شیفت در روز
        for staff in self.staff_data:
            staff_id = staff['id']
            for day in range(1, self.num_days + 1):
                self.model.Add(
                    sum(
                        self.shift_assignments[(staff_id, day, shift_code)]
                        for shift_code in staff['allowed_shifts']
                    ) <= 1
                )
        
        # ۲. پوشش نیاز روزانه
        for day in range(1, self.num_days + 1):
            is_holiday = day in self.holidays or day in self.weekend_days
            
            if is_holiday:
                requirements = {
                    'M': self.ward.holiday_min_staff_morning,
                    'E': self.ward.holiday_min_staff_evening,
                    'N': self.ward.holiday_min_staff_night
                }
            else:
                requirements = {
                    'M': self.ward.min_staff_morning,
                    'E': self.ward.min_staff_evening,
                    'N': self.ward.min_staff_night
                }
            
            for shift_type, required in requirements.items():
                if required > 0:
                    assigned_count = sum(
                        self.shift_assignments[(staff['id'], day, shift_code)]
                        for staff in self.staff_data
                        for shift_code in staff['allowed_shifts']
                        if shift_type in shift_code
                    )
                    self.model.Add(assigned_count == required)
        
        # ۳. حداکثر ساعات کاری
        for staff in self.staff_data:
            staff_id = staff['id']
            total_hours = sum(
                self.shift_assignments[(staff_id, day, shift_code)] * self.shift_durations[shift_code]
                for day in range(1, self.num_days + 1)
                for shift_code in staff['allowed_shifts']
            )
            self.model.Add(self.staff_hours[staff_id] == total_hours)
            self.model.Add(self.staff_hours[staff_id] <= staff['max_hours'])
        
        # ۴. آف بعد از شب
        for staff in self.staff_data:
            staff_id = staff['id']
            for day in range(1, self.num_days):
                night_today = sum(
                    self.shift_assignments[(staff_id, day, shift_code)]
                    for shift_code in staff['allowed_shifts']
                    if 'N' in shift_code
                )
                
                if day < self.num_days:
                    work_tomorrow = sum(
                        self.shift_assignments[(staff_id, day + 1, shift_code)]
                        for shift_code in staff['allowed_shifts']
                        if shift_code not in ['-', 'H']
                    )
                    self.model.Add(work_tomorrow <= 1 - night_today)
        
        # ۵. حداکثر شب‌های متوالی
        for staff in self.staff_data:
            staff_id = staff['id']
            for day in range(1, self.num_days - 3):
                consecutive_nights = sum(
                    sum(
                        self.shift_assignments[(staff_id, day + i, shift_code)]
                        for shift_code in staff['allowed_shifts']
                        if 'N' in shift_code
                    )
                    for i in range(5)
                )
                self.model.Add(consecutive_nights <= 4)
        
        # ۶. درخواست‌های شخصی
        for staff in self.staff_data:
            staff_id = staff['id']
            if staff_id in self.staff_requests:
                for day, requested_shift in self.staff_requests[staff_id].items():
                    if requested_shift == 'off':
                        self.model.Add(
                            sum(
                                self.shift_assignments[(staff_id, day, shift_code)]
                                for shift_code in staff['allowed_shifts']
                                if shift_code not in ['-', 'H']
                            ) == 0
                        )
                    else:
                        if requested_shift in staff['allowed_shifts']:
                            self.model.Add(
                                self.shift_assignments[(staff_id, day, requested_shift)] == 1
                            )
        
        # ۷. شمارش شب‌ها
        for staff in self.staff_data:
            staff_id = staff['id']
            night_count = sum(
                sum(
                    self.shift_assignments[(staff_id, day, shift_code)]
                    for shift_code in staff['allowed_shifts']
                    if 'N' in shift_code
                )
                for day in range(1, self.num_days + 1)
            )
            self.model.Add(self.staff_night_counts[staff_id] == night_count)
    
    def _add_objective(self):
        """تابع هدف"""
        if self.num_staff == 0:
            return
        
        avg_hours = sum(self.staff_hours[staff['id']] for staff in self.staff_data) / self.num_staff
        deviation_hours = sum(
            abs(self.staff_hours[staff['id']] - avg_hours)
            for staff in self.staff_data
        )
        
        max_nights = max(self.staff_night_counts[staff['id']] for staff in self.staff_data)
        min_nights = min(self.staff_night_counts[staff['id']] for staff in self.staff_data)
        
        self.model.Minimize(
            1.0 * deviation_hours +
            0.5 * (max_nights - min_nights)
        )
    
    def solve(self, time_limit=60):
        """حل مسئله"""
        self._load_data()
        
        if self.num_staff == 0:
            return None
        
        self._define_variables()
        self._add_constraints()
        self._add_objective()
        
        self.solver.parameters.max_time_in_seconds = time_limit
        self.solver.parameters.num_search_workers = 4
        
        start_time = time.time()
        status = self.solver.Solve(self.model)
        self.solving_time = time.time() - start_time
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            self.solution_found = True
            return self._extract_solution()
        else:
            return None
    
    def _extract_solution(self):
        """استخراج راه‌حل"""
        schedule = []
        
        for staff in self.staff_data:
            staff_schedule = {
                'staff_id': staff['id'],
                'staff_name': staff['name'],
                'days': []
            }
            
            for day in range(1, self.num_days + 1):
                assigned_shift = '-'
                for shift_code in staff['allowed_shifts']:
                    if (staff['id'], day, shift_code) in self.shift_assignments:
                        if self.solver.Value(self.shift_assignments[(staff['id'], day, shift_code)]) == 1:
                            assigned_shift = shift_code
                            break
                
                staff_schedule['days'].append({
                    'day': day,
                    'shift': assigned_shift
                })
            
            schedule.append(staff_schedule)
        
        return schedule
    
    def get_stats(self):
        """آمار حل"""
        return {
            'solving_time': self.solving_time,
            'solution_found': self.solution_found,
            'num_staff': self.num_staff,
            'num_days': self.num_days,
            'objective_value': self.solver.ObjectiveValue() if self.solution_found else None
        }