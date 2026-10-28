from django.core.management.base import BaseCommand
from api.models import Holiday
import requests
from datetime import datetime

class Command(BaseCommand):
    help = 'دریافت تعطیلات رسمی ایران از سایت ژئوفیزیک و ذخیره در دیتابیس'

    def add_arguments(self, parser):
        parser.add_argument('year', type=int, help='سال شمسی مورد نظر (مثلاً 1405)')

    def handle(self, *args, **options):
        year = options['year']
        self.stdout.write(f"⏳ در حال دریافت تعطیلات سال {year}...")
        
        # دریافت داده‌ها از سایت ژئوفیزیک
        # فرمت URL: https://calendar.ut.ac.ir/Holidays/GetList?StartDate=YYYY-MM-DD&EndDate=YYYY-MM-DD
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-29"
        
        url = f"https://calendar.ut.ac.ir/Holidays/GetList?StartDate={start_date}&EndDate={end_date}"
        
        try:
            response = requests.get(url)
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f'❌ خطا در ارتباط با سایت ژئوفیزیک: {response.status_code}'))
                return
            
            data = response.json()
            holidays = data.get('List', [])
            
            if not holidays:
                self.stdout.write(self.style.WARNING('⚠️ هیچ تعطیلاتی برای این سال یافت نشد.'))
                return
            
            # ذخیره در دیتابیس
            count = 0
            for item in holidays:
                date_str = item.get('Date')  # فرمت: YYYY-MM-DD
                name = item.get('Description')  # نام تعطیلات
                
                # تبدیل تاریخ به شمسی (اختیاری)
                if date_str and name:
                    obj, created = Holiday.objects.update_or_create(
                        date=date_str,
                        defaults={
                            'name': name,
                            'year': year
                        }
                    )
                    if created:
                        count += 1
                        self.stdout.write(f"✅ اضافه شد: {date_str} - {name}")
            
            self.stdout.write(self.style.SUCCESS(f'🎉 {count} تعطیلات با موفقیت برای سال {year} ذخیره شد.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ خطا: {str(e)}'))