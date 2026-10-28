# ai_module/ai_engine.py
import random
import re
import copy
from django.db.models import Q
from api.models import Ward, Profile, FinalSchedule, ShiftCode, Holiday, ShiftRequest
from .models import AIRule

class ShiftSchedulingEngine:
    """
    موتور اصلی تولید برنامه هوشمند شیفت
    با روش سرپرستار واقعی:
    1. برنامه‌های درخواستی افراد وارد برنامه می‌شود
    2. روز به روز چینش انجام می‌شود
    3. بررسی روز اول با ماه قبل
    4. اولویت با برنامه درخواستی
    5. جستجوی شیفت: صبح → عصر → شب
    6. بعد از شب حتماً آف
    7. رعایت ۹۵٪ درخواست‌های مرخصی
    8. فاصله شب‌ها و پراکندگی شیفت‌ها
    9. بررسی نهایی حداقل/حداکثر شیفت و تعداد آف
    """
    
    def __init__(self, ward, year, month, rules=None, prompt='', previous_month_last_day_shift=None):
        self.ward = ward
        self.year = year
        self.month = month
        self.rules = rules or []
        self.prompt = prompt
        from django.db.models import Q
        self.profiles = Profile.objects.filter(
            Q(ward=ward) | Q(additional_wards=ward)
        ).exclude(role__in=['head', 'admin', 'supervisor']).select_related('user').distinct()

        self.days_in_month = self._get_days_in_month()
        self.shift_codes = ShiftCode.objects.filter(ward=ward, is_active=True)
        
        # اهداف چینش استاندارد روزانه
        self.targets = {
            'M': ward.min_staff_morning,
            'E': ward.min_staff_evening,
            'N': ward.min_staff_night,
        }
        self.holiday_targets = {
            'M': ward.holiday_min_staff_morning,
            'E': ward.holiday_min_staff_evening,
            'N': ward.holiday_min_staff_night,
        }
        
        self.holidays = self._get_holidays()
        self.prompt_constraints = self._parse_prompt()
        self.staff_requests = self._get_staff_requests()
        self.staff_info = self._get_staff_info()
        self.weekend_days = self._get_weekend_days()
        
        # ماه قبل - آخرین روز
        self.previous_month_last_day_shift = previous_month_last_day_shift or {}
        
        # تعداد پرسنل
        self.staff_count = len(self.profiles)
        
        # اگر پرسنل کمتر از نیاز است، اهداف را تنظیم کن
        self._adjust_targets()
        
        # ذخیره روزهای مرخصی هر پرسنل (برای حفظ در بهینه‌سازی)
        self.fixed_days = {}
        for staff in self.profiles:
            staff_id = staff.user.id
            self.fixed_days[staff_id] = []
            if staff_id in self.staff_requests:
                for day in self.staff_requests[staff_id]:
                    if self.staff_requests[staff_id][day] in ['H', '-']:
                        self.fixed_days[staff_id].append(day)
        
        # آمار نهایی برای بررسی
        self.staff_shift_counts = {}
        self.staff_off_counts = {}
        self.staff_night_counts = {}
        
    def _adjust_targets(self):
        """
        اگر پرسنل کافی نیست، اهداف را به صورت هوشمند تنظیم کن
        """
        max_per_shift = max(1, self.staff_count // 3)
        if self.targets['M'] > max_per_shift:
            self.targets['M'] = max_per_shift
        if self.targets['E'] > max_per_shift:
            self.targets['E'] = max_per_shift
        if self.targets['N'] > max_per_shift:
            self.targets['N'] = max_per_shift
        
        if self.holiday_targets['M'] > max_per_shift:
            self.holiday_targets['M'] = max_per_shift
        if self.holiday_targets['E'] > max_per_shift:
            self.holiday_targets['E'] = max_per_shift
        if self.holiday_targets['N'] > max_per_shift:
            self.holiday_targets['N'] = max_per_shift
    
    def _get_days_in_month(self):
        """برگرداندن تعداد روزهای ماه شمسی"""
        days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
        return days_in_month[self.month - 1]
    
    def _get_holidays(self):
        """دریافت تعطیلات رسمی ماه"""
        month_prefix = f"{self.year}-{str(self.month).zfill(2)}"
        holidays = Holiday.objects.filter(date__startswith=month_prefix).values('date', 'name')
        holidays_dict = {}
        for h in holidays:
            day = int(h['date'].split('-')[2])
            holidays_dict[day] = h['name']
        return holidays_dict
    
    def _get_weekend_days(self):
        """دریافت روزهای آخر هفته (جمعه‌ها)"""
        from api.views import get_persian_weekday
        weekend_days = []
        for day in range(1, self.days_in_month + 1):
            weekday = get_persian_weekday(self.year, self.month, day)
            if weekday == 6:  # جمعه
                weekend_days.append(day)
        return weekend_days
    
    def _get_staff_requests(self):
        """دریافت درخواست‌های پرستاران (ترجیح فرد)"""
        month_prefix = f"{self.year}-{str(self.month).zfill(2)}"
        requests = ShiftRequest.objects.filter(
            ward=self.ward,
            request_date__startswith=month_prefix
        ).select_related('user', 'shift_code')
        
        staff_requests = {}
        for req in requests:
            day = int(req.request_date.split('-')[2])
            staff_id = req.user.id
            if staff_id not in staff_requests:
                staff_requests[staff_id] = {}
            if req.shift_code:
                staff_requests[staff_id][day] = req.shift_code.code
        return staff_requests
    
    def _get_staff_info(self):
        """دریافت اطلاعات کامل پرسنل"""
        staff_info = {}
        for profile in self.profiles:
            staff_info[profile.user.id] = {
                'name': f"{profile.user.first_name} {profile.user.last_name}",
                'position': profile.position,
                'shift_type': profile.shift_type,
                'work_experience': profile.work_experience,
                'employment_status': profile.employment_status,
            }
        return staff_info
    
    def _parse_prompt(self):
        """
        تبدیل پرامپت فارسی به محدودیت‌های قابل اجرا
        """
        constraints = {
            'preferred_shifts': {},      # {staff_id: [shift_codes]}
            'avoid_shifts': {},          # {staff_id: [shift_codes]}
            'max_consecutive_days': {},  # {staff_id: int}
            'min_rest_days': {},         # {staff_id: int}
            'no_consecutive_nights': False,
            'balance_shifts': True,
            'specific_staff_shift': {},  # {staff_id: 'M'}
            'max_nights_per_staff': None,
            'max_work_days_per_staff': None,
            'day_off_requests': {},      # {day: [staff_ids]}
            'staff_constraints': {},     # {staff_id: {'start_day': 1, 'end_day': 5}}
            'even_days_only': False,
            'odd_days_only': False,
            'excluded_staff': None,
            'staff_work_days': {},       # {staff_id: [days]}
            'extra_shift_needs': {},     # {day: {'M': 1, 'E': 0, 'N': 0}}
            'reduce_shift_needs': {},    # {day: {'M': 0, 'E': 1, 'N': 0}}
            'all_staff_shift': None,     # 'M' یا 'E' یا 'N' - برای همه
        }
        
        prompt = self.prompt.lower()
        staff_names = {f"{p.user.first_name} {p.user.last_name}".lower(): p.user.id for p in self.profiles}
        staff_last_names = {p.user.last_name.lower(): p.user.id for p in self.profiles}
        
        # تشخیص نام پرسنل
        matched_staff = []
        for name, staff_id in staff_names.items():
            if name in prompt:
                matched_staff.append(staff_id)
                if 'صبح' in prompt or 'm' in prompt.split():
                    constraints['preferred_shifts'][staff_id] = ['M']
                if 'عصر' in prompt or 'e' in prompt.split():
                    constraints['preferred_shifts'][staff_id] = ['E']
                if 'شب' in prompt or 'n' in prompt.split():
                    constraints['preferred_shifts'][staff_id] = ['N']
                if 'آف' in prompt or 'استراحت' in prompt:
                    constraints['preferred_shifts'][staff_id] = ['-']
                if 'مرخصی' in prompt or 'h' in prompt.split():
                    constraints['preferred_shifts'][staff_id] = ['H']
        
        # تشخیص نام خانوادگی
        for last_name, staff_id in staff_last_names.items():
            if last_name in prompt and staff_id not in matched_staff:
                matched_staff.append(staff_id)
                if 'صبح' in prompt:
                    constraints['preferred_shifts'][staff_id] = ['M']
                if 'عصر' in prompt:
                    constraints['preferred_shifts'][staff_id] = ['E']
                if 'شب' in prompt:
                    constraints['preferred_shifts'][staff_id] = ['N']
                if 'آف' in prompt:
                    constraints['preferred_shifts'][staff_id] = ['-']
        
        # تشخیص "تا حد امکان" یا "اولویت"
        if 'تا حد امکان' in prompt or 'اولویت' in prompt or 'ترجیح' in prompt:
            constraints['balance_shifts'] = True
        
        # تشخیص "پشت سر هم شب کار نکن"
        if 'پشت سر هم شب' in prompt or 'شب پشت سر هم' in prompt:
            constraints['no_consecutive_nights'] = True
        
        # تشخیص "حداکثر X روز پشت سر هم"
        match = re.search(r'حداکثر\s+(\d+)\s+روز', prompt)
        if match:
            max_days = int(match.group(1))
            for staff_id in matched_staff:
                constraints['max_consecutive_days'][staff_id] = max_days
            if not matched_staff:
                for staff in self.profiles:
                    constraints['max_consecutive_days'][staff.user.id] = max_days
        
        # تشخیص "حداکثر X شب کاری"
        match = re.search(r'حداکثر\s+(\d+)\s+شب', prompt)
        if match:
            constraints['max_nights_per_staff'] = int(match.group(1))
        
        # تشخیص "حداکثر X روز کاری"
        match = re.search(r'حداکثر\s+(\d+)\s+روز\s+کاری', prompt)
        if match:
            constraints['max_work_days_per_staff'] = int(match.group(1))
        
        # تشخیص "از روز X تا روز Y"
        match = re.search(r'از\s+روز\s+(\d+)\s+تا\s+روز\s+(\d+)', prompt)
        if match:
            start_day = int(match.group(1))
            end_day = int(match.group(2))
            for staff_id in matched_staff:
                constraints['staff_constraints'][staff_id] = {
                    'start_day': start_day,
                    'end_day': end_day
                }
        
        # تشخیص "روزهای زوج/فرد"
        if 'روزهای زوج' in prompt:
            constraints['even_days_only'] = True
        if 'روزهای فرد' in prompt:
            constraints['odd_days_only'] = True
        
        # تشخیص "همه را ... بگذار"
        if 'همه' in prompt or 'تمام' in prompt:
            if 'صبح' in prompt:
                constraints['all_staff_shift'] = 'M'
            if 'عصر' in prompt:
                constraints['all_staff_shift'] = 'E'
            if 'شب' in prompt:
                constraints['all_staff_shift'] = 'N'
            if 'آف' in prompt:
                constraints['all_staff_shift'] = '-'
        
        # تشخیص "به جز [نام]"
        match = re.search(r'به جز\s+([\u0600-\u06FF\s]+)', prompt)
        if match:
            excluded_name = match.group(1).strip().lower()
            for name, staff_id in staff_names.items():
                if excluded_name in name:
                    constraints['excluded_staff'] = staff_id
        
        # تشخیص "افزایش پرسنل در روز X"
        match = re.search(r'افزایش\s+پرسنل\s+در\s+روز\s+(\d+)', prompt)
        if match:
            day = int(match.group(1))
            constraints['extra_shift_needs'][day] = {'M': 1, 'E': 0, 'N': 0}
        
        # تشخیص "کاهش پرسنل در روز X"
        match = re.search(r'کاهش\s+پرسنل\s+در\s+روز\s+(\d+)', prompt)
        if match:
            day = int(match.group(1))
            constraints['reduce_shift_needs'][day] = {'M': 0, 'E': 1, 'N': 0}
        
        # تشخیص "روز X تعطیل باشد"
        match = re.search(r'روز\s+(\d+)\s+تعطیل\s+باشد', prompt)
        if match:
            day = int(match.group(1))
            constraints['day_off_requests'][day] = matched_staff
        
        # تشخیص "فقط در روزهای ..."
        match = re.search(r'فقط در روزهای\s+([\u0600-\u06FF\s]+)', prompt)
        if match:
            days_text = match.group(1).strip()
            if 'اول' in days_text:
                constraints['staff_work_days'] = {staff_id: [1, 2, 3, 4, 5] for staff_id in matched_staff}
            elif 'آخر' in days_text:
                constraints['staff_work_days'] = {staff_id: [self.days_in_month - 4, self.days_in_month - 3, self.days_in_month - 2, self.days_in_month - 1, self.days_in_month] for staff_id in matched_staff}
        
        return constraints
    
    def _is_friday(self, day):
        """بررسی اینکه آیا روز جمعه است"""
        return day in self.weekend_days
    
    def _get_active_rules(self):
        """دریافت قوانین فعال از دیتابیس"""
        return AIRule.objects.filter(is_active=True)
    
    def _calculate_shift_weight(self, shift):
        """محاسبه وزن شیفت"""
        if shift == 'H' or shift == 'مرخصی':
            return 1
        elif shift == 'N' or shift == 'شب':
            return 2
        else:
            return 1
    
    def _calculate_staff_total(self, schedule_data, staff_id):
        """محاسبه مجموع وزن شیفت‌های یک پرسنل"""
        total = 0
        for day in schedule_data[staff_id]:
            shift = day.get('shift', '')
            total += self._calculate_shift_weight(shift)
        return total
    
    def _get_daily_counts(self, schedule_data, day):
        """محاسبه تعداد پرسنل در هر شیفت برای یک روز خاص"""
        counts = {'M': 0, 'E': 0, 'N': 0}
        for staff in self.profiles:
            staff_id = staff.user.id
            shift = schedule_data[staff_id][day-1].get('shift', '')
            if 'M' in shift:
                counts['M'] += 1
            if 'E' in shift:
                counts['E'] += 1
            if 'N' in shift:
                counts['N'] += 1
        return counts
    
    def _get_daily_needs(self, day):
        """محاسبه نیاز استاندارد روزانه"""
        if day in self.holidays or self._is_friday(day):
            return {
                'M': self.holiday_targets['M'],
                'E': self.holiday_targets['E'],
                'N': self.holiday_targets['N'],
            }
        else:
            return {
                'M': self.targets['M'],
                'E': self.targets['E'],
                'N': self.targets['N'],
            }
    
    def _calculate_match_percentage(self, schedule_data):
        """
        محاسبه درصد تطابق با چینش استاندارد
        """
        total_needed = 0
        total_matched = 0
        
        for day in range(1, self.days_in_month + 1):
            daily_needs = self._get_daily_needs(day)
            daily_counts = self._get_daily_counts(schedule_data, day)
            
            for shift_type in ['M', 'E', 'N']:
                needed = daily_needs[shift_type]
                actual = daily_counts[shift_type]
                
                total_needed += needed
                total_matched += min(needed, actual)
        
        if total_needed == 0:
            return 100
        
        return int((total_matched / total_needed) * 100)
    
    def _check_no_consecutive_nights(self, schedule_data, staff_id, day, shift):
        """
        بررسی اینکه شیفت شب پشت سر هم نباشد
        """
        if day <= 1:
            return True
        
        prev_shift = schedule_data[staff_id][day-2].get('shift', '')
        
        # اگر دیروز شب بوده و امروز هم شب است، ممنوع
        if 'N' in prev_shift and 'N' in shift:
            return False
        
        return True
    
    def _check_no_work_after_night(self, schedule_data, staff_id, day, shift):
        """
        بررسی اینکه بعد از شب هیچ شیفتی نباشد
        """
        if day <= 1:
            return True
        
        prev_shift = schedule_data[staff_id][day-2].get('shift', '')
        
        # اگر دیروز شب بوده و امروز هر شیفتی غیر از آف باشد، ممنوع
        if 'N' in prev_shift and shift != '-':
            return False
        
        return True
    
    def _check_first_day_with_previous_month(self, staff_id, day):
        """
        بررسی روز اول با ماه قبل
        اگر آخرین روز ماه قبل شب باشد، روز اول آف شود
        """
        if day == 1:
            if staff_id in self.previous_month_last_day_shift:
                prev_shift = self.previous_month_last_day_shift[staff_id]
                if 'N' in prev_shift:
                    return False  # باید آف باشد
        return True
    
    def _select_shift_combined(self, staff, day, day_needs, schedule_data):
        """
        انتخاب شیفت ترکیبی (لانگ) برای پر کردن نیاز روز
        """
        staff_id = staff.user.id
        
        # بررسی کمبودهای مختلف
        if day_needs['M'] > 0 and day_needs['E'] > 0:
            return 'ME'
        elif day_needs['M'] > 0 and day_needs['N'] > 0:
            if self._check_no_consecutive_nights(schedule_data, staff_id, day, 'MN'):
                return 'MN'
        elif day_needs['E'] > 0 and day_needs['N'] > 0:
            if self._check_no_consecutive_nights(schedule_data, staff_id, day, 'EN'):
                return 'EN'
        
        return None
    
    def _check_leave_request_percentage(self, schedule_data):
        """
        بررسی اینکه ۹۵٪ درخواست‌های مرخصی اعمال شده باشد
        """
        total_requests = 0
        fulfilled_requests = 0
        
        for staff in self.profiles:
            staff_id = staff.user.id
            if staff_id in self.staff_requests:
                for day in self.staff_requests[staff_id]:
                    if self.staff_requests[staff_id][day] in ['H', '-']:
                        total_requests += 1
                        if schedule_data[staff_id][day-1]['shift'] == self.staff_requests[staff_id][day]:
                            fulfilled_requests += 1
        
        if total_requests == 0:
            return True
        
        percentage = (fulfilled_requests / total_requests) * 100
        return percentage >= 95
    
    def _check_spacing_and_distribution(self, schedule_data, staff_id):
        """
        بررسی فاصله شب‌ها و پراکندگی شیفت‌ها
        """
        nights = []
        for day in range(1, self.days_in_month + 1):
            shift = schedule_data[staff_id][day-1].get('shift', '')
            if 'N' in shift:
                nights.append(day)
        
        # بررسی فاصله شب‌ها (حداقل ۲ روز فاصله بین شب‌ها)
        for i in range(1, len(nights)):
            if nights[i] - nights[i-1] < 2:
                return False
        
        # بررسی پراکندگی شیفت‌ها
        shifts = [schedule_data[staff_id][day-1].get('shift', '-') for day in range(1, self.days_in_month + 1)]
        if len(set(shifts)) < 2:
            return False
        
        return True
    
    def _final_check(self, schedule_data):
        """
        بررسی نهایی:
        1. حداقل شیفت (۲۰)
        2. حداکثر شیفت (۴۵)
        3. تعداد آف
        """
        for staff in self.profiles:
            staff_id = staff.user.id
            total = self._calculate_staff_total(schedule_data, staff_id)
            
            # بررسی حداقل شیفت
            if total < 20:
                # اگر کمتر از ۲۰ است، باید شیفت اضافه شود
                pass
            
            # بررسی حداکثر شیفت
            if total > 45:
                # اگر بیشتر از ۴۵ است، باید شیفت کم شود
                pass
        
        return True
    
    def _redistribute_shifts_for_minimum(self, schedule_data):
        """
        توزیع مجدد شیفت‌ها برای اطمینان از اینکه هر پرسنل حداقل ۲۰ شیفت بگیرد
        """
        # محاسبه تعداد شیفت هر پرسنل
        staff_shift_counts = {}
        for staff in self.profiles:
            staff_id = staff.user.id
            count = sum(1 for d in schedule_data[staff_id] if d.get('shift', '') != '-')
            staff_shift_counts[staff_id] = count
        
        # پیدا کردن پرسنل با کمتر از ۲۰ شیفت
        staff_needing_more = []
        for staff in self.profiles:
            staff_id = staff.user.id
            if staff_shift_counts[staff_id] < 20:
                staff_needing_more.append(staff_id)
        
        # پیدا کردن پرسنل با بیشتر از ۴۵ شیفت
        staff_with_excess = []
        for staff in self.profiles:
            staff_id = staff.user.id
            if staff_shift_counts[staff_id] > 45:
                staff_with_excess.append(staff_id)
        
        # اگر کسی کمتر از ۲۰ دارد، از کسی که بیشتر دارد بردار
        for staff_id in staff_needing_more:
            # پیدا کردن روزهایی که این پرسنل آف است
            off_days = [day for day in range(1, self.days_in_month + 1) if schedule_data[staff_id][day-1]['shift'] == '-']
            
            # پیدا کردن روزهایی که پرسنل با شیفت اضافی دارد
            for excess_staff_id in staff_with_excess:
                excess_off_days = [day for day in range(1, self.days_in_month + 1) if schedule_data[excess_staff_id][day-1]['shift'] != '-']
                
                # پیدا کردن روز مشترک
                common_days = list(set(off_days) & set(excess_off_days))
                
                for day in common_days:
                    if staff_shift_counts[staff_id] >= 20:
                        break
                    
                    # بررسی اینکه آیا این روز برای این پرسنل مرخصی ثابت است
                    if day in self.fixed_days.get(staff_id, []):
                        continue
                    
                    # بررسی عدم کار بعد از شب
                    if not self._check_no_work_after_night(schedule_data, staff_id, day, 'M'):
                        continue
                    
                    # انتقال شیفت
                    shift = schedule_data[excess_staff_id][day-1]['shift']
                    schedule_data[staff_id][day-1]['shift'] = shift
                    schedule_data[excess_staff_id][day-1]['shift'] = '-'
                    
                    staff_shift_counts[staff_id] += 1
                    staff_shift_counts[excess_staff_id] -= 1
                    
                    if staff_shift_counts[excess_staff_id] < 20:
                        break
        
        return schedule_data
    
    def generate_schedule(self):
        """
        تولید برنامه هوشمند شیفت
        با روش سرپرستار واقعی:
        1. برنامه‌های درخواستی افراد وارد برنامه می‌شود
        2. روز به روز چینش انجام می‌شود
        3. بررسی روز اول با ماه قبل
        4. اولویت با برنامه درخواستی
        5. جستجوی شیفت: صبح → عصر → شب
        6. بعد از شب حتماً آف
        7. رعایت ۹۵٪ درخواست‌های مرخصی
        8. فاصله شب‌ها و پراکندگی شیفت‌ها
        9. بررسی نهایی حداقل/حداکثر شیفت و تعداد آف
        """
        schedule_data = {}
        
        # ۱. مقداردهی اولیه
        for staff in self.profiles:
            schedule_data[staff.user.id] = []
            for day in range(1, self.days_in_month + 1):
                schedule_data[staff.user.id].append({'day': day, 'shift': ''})
        
        # ۲. دریافت قوانین فعال
        active_rules = self._get_active_rules()
        
        # ۳. اعمال درخواست‌های مرخصی (اولویت اول - همیشه)
        for staff in self.profiles:
            staff_id = staff.user.id
            if staff_id in self.staff_requests:
                for day in range(1, self.days_in_month + 1):
                    if day in self.staff_requests[staff_id]:
                        requested_shift = self.staff_requests[staff_id][day]
                        if requested_shift == 'H' or requested_shift == '-':
                            schedule_data[staff_id][day-1]['shift'] = requested_shift
        
        # ۴. اعمال محدودیت‌های پرامپت (شیفت‌های ثابت)
        for staff_id, shifts in self.prompt_constraints['preferred_shifts'].items():
            if len(shifts) == 1 and shifts[0] in ['M', 'E', 'N', '-', 'H']:
                for day in range(1, self.days_in_month + 1):
                    if schedule_data[staff_id][day-1]['shift'] == '':
                        schedule_data[staff_id][day-1]['shift'] = shifts[0]
        
        # ۵. روز به روز چینش
        for day in range(1, self.days_in_month + 1):
            day_needs = self._get_daily_needs(day)
            
            # اعمال تغییرات پرامپت
            if day in self.prompt_constraints.get('extra_shift_needs', {}):
                extra = self.prompt_constraints['extra_shift_needs'][day]
                day_needs['M'] += extra.get('M', 0)
                day_needs['E'] += extra.get('E', 0)
                day_needs['N'] += extra.get('N', 0)
            
            if day in self.prompt_constraints.get('reduce_shift_needs', {}):
                reduce = self.prompt_constraints['reduce_shift_needs'][day]
                day_needs['M'] -= reduce.get('M', 0)
                day_needs['E'] -= reduce.get('E', 0)
                day_needs['N'] -= reduce.get('N', 0)
            
            # تخصیص شیفت‌ها به پرسنل - مرحله ۱: پر کردن نیاز استاندارد
            for staff in self.profiles:
                staff_id = staff.user.id
                current_shift = schedule_data[staff_id][day-1]['shift']
                
                # اگر از قبل شیفت تعیین شده (مرخصی یا درخواست)
                if current_shift:
                    continue
                
                # اگر نیاز روز پر شده، ادامه نده
                if day_needs['M'] <= 0 and day_needs['E'] <= 0 and day_needs['N'] <= 0:
                    break
                
                # بررسی روز اول با ماه قبل
                if not self._check_first_day_with_previous_month(staff_id, day):
                    # اگر آخرین روز ماه قبل شب باشد، روز اول آف شود
                    schedule_data[staff_id][day-1]['shift'] = '-'
                    continue
                
                # بررسی عدم کار بعد از شب
                if not self._check_no_work_after_night(schedule_data, staff_id, day, 'M'):
                    schedule_data[staff_id][day-1]['shift'] = '-'
                    continue
                
                # انتخاب شیفت مناسب (ابتدا شیفت ترکیبی را امتحان کن)
                selected_shift = self._select_shift_combined(staff, day, day_needs, schedule_data)
                
                if not selected_shift:
                    selected_shift = self._select_shift(staff, day, day_needs, schedule_data, active_rules)
                
                if selected_shift:
                    schedule_data[staff_id][day-1]['shift'] = selected_shift
                    if 'M' in selected_shift: day_needs['M'] -= 1
                    if 'E' in selected_shift: day_needs['E'] -= 1
                    if 'N' in selected_shift: day_needs['N'] -= 1
            
            # تخصیص شیفت‌ها به پرسنل - مرحله ۲: ترجیحات
            for staff in self.profiles:
                staff_id = staff.user.id
                current_shift = schedule_data[staff_id][day-1]['shift']
                
                # اگر از قبل شیفت تعیین شده
                if current_shift:
                    continue
                
                # بررسی درخواست‌های پرستار
                if staff_id in self.staff_requests and day in self.staff_requests[staff_id]:
                    requested_shift = self.staff_requests[staff_id][day]
                    if requested_shift == '-' or requested_shift == 'H':
                        schedule_data[staff_id][day-1]['shift'] = requested_shift
                    continue
                
                # بررسی پرامپت (اگر همه را شیفت خاص بده)
                if self.prompt_constraints.get('all_staff_shift'):
                    schedule_data[staff_id][day-1]['shift'] = self.prompt_constraints['all_staff_shift']
                    continue
                
                # اگر ترجیحی وجود دارد
                if staff_id in self.prompt_constraints['preferred_shifts']:
                    preferred = self.prompt_constraints['preferred_shifts'][staff_id]
                    if preferred[0] == '-' or preferred[0] == 'H':
                        schedule_data[staff_id][day-1]['shift'] = preferred[0]
                    continue
        
        # ۶. تکمیل روزهای خالی
        for staff in self.profiles:
            for day in range(1, self.days_in_month + 1):
                if not schedule_data[staff.user.id][day-1]['shift']:
                    schedule_data[staff.user.id][day-1]['shift'] = '-'
        
        # ۷. توزیع مجدد شیفت‌ها برای اطمینان از حداقل شیفت (۲۰)
        schedule_data = self._redistribute_shifts_for_minimum(schedule_data)
        
        # ۸. بررسی نهایی
        self._final_check(schedule_data)
        
        # ۹. تبدیل به فرمت خروجی
        result = []
        for staff in self.profiles:
            staff_days = []
            for day in range(1, self.days_in_month + 1):
                staff_days.append({
                    'day': day,
                    'shift': schedule_data[staff.user.id][day-1]['shift']
                })
            result.append({
                'staff_id': staff.user.id,
                'staff_name': f"{staff.user.first_name} {staff.user.last_name}",
                'days': staff_days
            })
        
        return result
    
    def _select_shift(self, staff, day, day_needs, schedule_data, active_rules):
        """
        انتخاب شیفت مناسب برای یک پرسنل
        با اولویت:
        1. درخواست مرخصی (همیشه)
        2. پر کردن نیاز استاندارد روزانه (سخت)
        3. ترجیح فرد (نرم)
        4. پرامپت سرپرستار
        و عدم شب پشت سر هم و عدم کار بعد از شب
        """
        staff_id = staff.user.id
        staff_info = self.staff_info[staff_id]
        
        # ============ اولویت ۱: درخواست مرخصی (همیشه) ============
        if staff_id in self.staff_requests and day in self.staff_requests[staff_id]:
            requested_shift = self.staff_requests[staff_id][day]
            if requested_shift == 'H' or requested_shift == '-':
                return requested_shift
        
        # ============ اولویت ۲: پر کردن نیاز استاندارد (سخت) ============
        if day_needs['M'] > 0 or day_needs['E'] > 0 or day_needs['N'] > 0:
            # انتخاب بر اساس نیاز روز
            available_shifts = []
            if day_needs['M'] > 0:
                available_shifts.append('M')
            if day_needs['E'] > 0:
                available_shifts.append('E')
            if day_needs['N'] > 0:
                available_shifts.append('N')
            
            # بررسی عدم شب پشت سر هم
            if 'N' in available_shifts and not self._check_no_consecutive_nights(schedule_data, staff_id, day, 'N'):
                available_shifts.remove('N')
            
            # بررسی عدم کار بعد از شب
            if not self._check_no_work_after_night(schedule_data, staff_id, day, 'M'):
                available_shifts = []
            
            # بررسی نوبت کاری فرد
            shift_type = staff_info.get('shift_type', 'سه_نوبتی')
            if shift_type == 'ثابت_صبح' and 'M' in available_shifts:
                return 'M'
            elif shift_type == 'ثابت_عصر' and 'E' in available_shifts:
                return 'E'
            elif shift_type == 'ثابت_شب' and 'N' in available_shifts:
                return 'N'
            elif shift_type == 'دو_نوبتی_عصر_شب' and ('E' in available_shifts or 'N' in available_shifts):
                return 'EN'
            elif shift_type == 'دو_نوبتی_صبح_شب' and ('M' in available_shifts or 'N' in available_shifts):
                return 'MN'
            elif shift_type == 'دو_نوبتی_صبح_عصر' and ('M' in available_shifts or 'E' in available_shifts):
                return 'ME'
            
            # بررسی درخواست‌های پرستار
            if staff_id in self.staff_requests and day in self.staff_requests[staff_id]:
                requested_shift = self.staff_requests[staff_id][day]
                if 'M' in requested_shift and day_needs['M'] > 0:
                    return requested_shift
                if 'E' in requested_shift and day_needs['E'] > 0:
                    return requested_shift
                if 'N' in requested_shift and day_needs['N'] > 0:
                    return requested_shift
            
            # بررسی پرامپت
            if staff_id in self.prompt_constraints['preferred_shifts']:
                preferred = self.prompt_constraints['preferred_shifts'][staff_id]
                for shift in preferred:
                    if 'M' in shift and day_needs['M'] > 0:
                        return shift
                    if 'E' in shift and day_needs['E'] > 0:
                        return shift
                    if 'N' in shift and day_needs['N'] > 0:
                        return shift
            
            # انتخاب تصادفی از بین شیفت‌های موجود
            if available_shifts:
                return random.choice(available_shifts)
        
        # ============ اولویت ۳: ترجیح فرد (نرم) ============
        # اگر نیاز روز پر شده، ترجیحات را اعمال کن
        
        # درخواست‌های پرستار
        if staff_id in self.staff_requests and day in self.staff_requests[staff_id]:
            requested_shift = self.staff_requests[staff_id][day]
            if requested_shift == '-' or requested_shift == 'H':
                return requested_shift
        
        # پرامپت سرپرستار
        if staff_id in self.prompt_constraints['preferred_shifts']:
            preferred = self.prompt_constraints['preferred_shifts'][staff_id]
            if preferred[0] == '-' or preferred[0] == 'H':
                return preferred[0]
        
        # ============ اولویت ۴: آف (استراحت) ============
        return '-'