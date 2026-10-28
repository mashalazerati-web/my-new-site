# api/management/commands/migrate_schedule_statuses.py
# اگر پوشه management/commands وجود ندارد، بسازید

from django.core.management.base import BaseCommand
from django.db.models import Q
from api.models import FinalSchedule, DraftSchedule, MonthlyScheduleStatus, ScheduleStatus


class Command(BaseCommand):
    help = 'مهاجرت وضعیت‌های موجود FinalSchedule به MonthlyScheduleStatus'

    def handle(self, *args, **options):
        self.stdout.write('🔄 شروع مهاجرت وضعیت‌ها...')

        # جمع‌آوری همه ترکیب‌های (ward, year, month, schedule_type)
        combos = set()

        for fs in FinalSchedule.objects.all().values('ward_id', 'schedule_date', 'schedule_type'):
            parts = fs['schedule_date'].split('-')
            if len(parts) == 3:
                year, month = int(parts[0]), int(parts[1])
                combos.add((fs['ward_id'], year, month, fs['schedule_type']))

        for ds in DraftSchedule.objects.filter(source='manual').values('ward_id', 'schedule_date', 'schedule_type'):
            parts = ds['schedule_date'].split('-')
            if len(parts) == 3:
                year, month = int(parts[0]), int(parts[1])
                combos.add((ds['ward_id'], year, month, ds['schedule_type']))

        created_count = 0
        updated_count = 0

        for ward_id, year, month, schedule_type in combos:
            # وضعیت از FinalSchedule گرفته می‌شود
            first_final = FinalSchedule.objects.filter(
                ward_id=ward_id,
                schedule_date__startswith=f"{year}-{str(month).zfill(2)}",
                schedule_type=schedule_type
            ).first()

            if first_final:
                server_status = first_final.status
            else:
                server_status = ScheduleStatus.DRAFT

            obj, created = MonthlyScheduleStatus.objects.update_or_create(
                ward_id=ward_id,
                year=year,
                month=month,
                schedule_type=schedule_type,
                defaults={'status': server_status}
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ مهاجرت کامل شد. {created_count} رکورد جدید، {updated_count} رکورد به‌روزرسانی شد.'
        ))