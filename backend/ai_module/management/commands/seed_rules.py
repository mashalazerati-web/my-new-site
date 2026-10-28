# ai_module/management/commands/seed_rules.py
from django.core.management.base import BaseCommand
from ai_module.models import AIRule  # ✅ ایمپورت از مسیر کامل

class Command(BaseCommand):
    help = 'ایجاد قوانین پیش‌فرض هوش مصنوعی'

    def handle(self, *args, **kwargs):
        rules = [
            {'name': 'تعداد روزهای برنامه', 'description': 'تعداد روزهای برنامه بر اساس ماه و تقویم شمسی', 'logic_code': 'days_in_month'},
            {'name': 'تعطیلات رسمی و جمعه‌ها', 'description': 'روزهای تعطیلات رسمی و جمعه‌ها از تقویم شمسی', 'logic_code': 'holidays'},
            {'name': 'حداقل شیفت (۲۰)', 'description': 'حداقل تعداد شیفت فرد باید ۲۰ باشد. هر مرخصی یک شیفت و هر شب دو شیفت محاسبه می‌شود.', 'logic_code': 'min_shifts'},
            {'name': 'حداکثر شیفت (۴۵)', 'description': 'حداکثر تعداد شیفت فرد باید ۴۵ باشد. هر مرخصی یک شیفت و هر شب دو شیفت محاسبه می‌شود.', 'logic_code': 'max_shifts'},
            {'name': 'تأثیر مرخصی بر حداقل', 'description': 'تعداد مرخصی از تعداد کل شیفت‌های فرد کسر شود و به همان نسبت حداقل تعداد کاهش یابد.', 'logic_code': 'leave_impact'},
            {'name': 'اولویت برنامه درخواستی', 'description': 'شیفت‌های درخواستی فرد در اولویت باشد و ترجیحاً مد نظر قرار گیرد', 'logic_code': 'request_priority'},
            {'name': 'نوبت کاری فرد در اولویت', 'description': 'شیفت‌های فرد در اولویت باشد و ترجیحاً مد نظر قرار گیرد', 'logic_code': 'shift_type_priority'},
            {'name': 'تقسیم شیفت‌های آخر هفته', 'description': 'افراد با سابقه پایین تعداد بیشتری از آخر هفته داشته باشند', 'logic_code': 'weekend_distribution'},
            {'name': 'ترکیب تجربه افراد', 'description': 'به ازای هر نفر حداقل دو سال تجربه کاری نیاز باشد', 'logic_code': 'experience_mix'},
            {'name': 'توزیع انواع شیفت', 'description': 'شیفت‌های فرد در طول ماه توزیع گردد و پراکندگی خوبی داشته باشد', 'logic_code': 'shift_distribution'},
        ]

        for rule_data in rules:
            rule, created = AIRule.objects.get_or_create(
                name=rule_data['name'],
                defaults=rule_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ قانون "{rule.name}" ایجاد شد.'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ قانون "{rule.name}" از قبل وجود دارد.'))

        self.stdout.write(self.style.SUCCESS('🎉 تمام قوانین با موفقیت ایجاد شدند!'))