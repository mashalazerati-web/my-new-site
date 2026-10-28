# api/workflow.py

from django.contrib.auth.models import User
from .models import FinalSchedule, MonthlyScheduleStatus, ScheduleStatus


class WorkflowError(Exception):
    """خطای سفارشی برای گردش کار"""
    pass


def schedule_type_label(schedule_type):
    """برچسب فارسی نوع برنامه"""
    return {
        'main': 'اصلی',
        'oncall': 'آنکالی',
        'crisis': 'بحران',
        'assistant': 'کمک پرستار',   # ✅ جدید
    }.get(schedule_type, schedule_type)


STATUS_LABELS_FA = {
    'DRAFT': 'پیش‌نویس',
    'PENDING_SUPERVISOR': 'در انتظار تایید سوپروایزر',
    'PENDING_MATRON': 'در انتظار تایید نهایی مترون',
    'LOCKED': 'قفل شده',
    'RETURNED_TO_HEAD': 'بازگشته به سرپرستار',
    'RETURNED_TO_SUPERVISOR': 'بازگشته به سوپروایزر',
}


class WorkflowEngine:
    """
    کلاس متمرکز برای مدیریت تمام حالت‌ها و تراکنش‌های گردش کار.
    """

    # ========================================================
    # قوانین وابستگی بین برنامه‌ها
    # ========================================================
    DEPENDENCY_RULES = {
        'main': {
            'requires': [],
            'can_generate_in_statuses': ['DRAFT', 'RETURNED_TO_HEAD'],
        },
        'oncall': {
            'requires': [('main', ['PENDING_SUPERVISOR', 'PENDING_MATRON', 'LOCKED'])],
            'can_generate_in_statuses': ['DRAFT', 'RETURNED_TO_HEAD'],
        },
        'crisis': {
            'requires': [('main', ['PENDING_SUPERVISOR', 'PENDING_MATRON', 'LOCKED'])],
            'can_generate_in_statuses': ['DRAFT', 'RETURNED_TO_HEAD'],
        },
        # ✅ برنامه کمک پرستار — مستقل از main
        'assistant': {
            'requires': [],
            'can_generate_in_statuses': ['DRAFT', 'RETURNED_TO_HEAD'],
        },
    }

    # ========================================================
    # بررسی امکان ویرایش
    # ========================================================
    @staticmethod
    def can_edit(schedule, user):
        if user.profile.role != 'head':
            return False
        return schedule.status in [ScheduleStatus.DRAFT, ScheduleStatus.RETURNED_TO_HEAD]

    # ========================================================
    # بررسی امکان تایید
    # ========================================================
    @staticmethod
    def can_approve(current_status, actor_role, schedule_type='main'):
        if current_status == ScheduleStatus.DRAFT:
            return actor_role == 'head'
        if current_status == ScheduleStatus.PENDING_SUPERVISOR:
            return actor_role == 'supervisor'
        if current_status == ScheduleStatus.PENDING_MATRON:
            return actor_role == 'admin'
        if current_status == ScheduleStatus.RETURNED_TO_SUPERVISOR:
            return actor_role == 'supervisor'
        if current_status == ScheduleStatus.RETURNED_TO_HEAD:
            return actor_role == 'head'
        return False

    # ========================================================
    # تایید
    # ========================================================
    @staticmethod
    def approve(current_status, actor_role, schedule_type='main'):
        if not WorkflowEngine.can_approve(current_status, actor_role, schedule_type):
            raise WorkflowError(
                f"عملیات تایید برای وضعیت '{current_status}' و نقش '{actor_role}' مجاز نیست."
            )
        if actor_role == 'head':
            return ScheduleStatus.PENDING_SUPERVISOR
        if actor_role == 'supervisor':
            return ScheduleStatus.PENDING_MATRON
        if actor_role == 'admin':
            return ScheduleStatus.LOCKED
        raise WorkflowError("نقش نامعتبر برای تایید.")

    # ========================================================
    # بازگردانی
    # ========================================================
    @staticmethod
    def reject(current_status, actor_role, reason, schedule_type='main'):
        if not reason or not reason.strip():
            raise WorkflowError("دلیل بازگردانی الزامی است.")
        if actor_role == 'supervisor':
            if current_status not in (ScheduleStatus.PENDING_SUPERVISOR, ScheduleStatus.RETURNED_TO_SUPERVISOR):
                raise WorkflowError(f"سوپروایزر در وضعیت '{current_status}' نمی‌تواند بازگردانی کند.")
            return ScheduleStatus.RETURNED_TO_HEAD, reason
        if actor_role == 'admin':
            if current_status != ScheduleStatus.PENDING_MATRON:
                raise WorkflowError(f"مترون در وضعیت '{current_status}' نمی‌تواند بازگردانی کند.")
            return ScheduleStatus.RETURNED_TO_SUPERVISOR, reason
        raise WorkflowError(f"نقش '{actor_role}' اجازه بازگردانی ندارد.")

    # ========================================================
    # ریست
    # ========================================================
    @staticmethod
    def reset(current_status, actor_role, schedule_type='main'):
        if current_status == ScheduleStatus.LOCKED:
            if actor_role == 'admin':
                return ScheduleStatus.DRAFT
            raise WorkflowError("فقط مترون می‌تواند برنامه قفل شده را به حالت اولیه بازگرداند.")
        raise WorkflowError("فقط برنامه‌های قفل شده را می‌توان به حالت اولیه بازگرداند.")

    # ========================================================
    # توابع کمکی
    # ========================================================
    @staticmethod
    def get_or_create_status(ward, year, month, schedule_type='main'):
        status_obj, created = MonthlyScheduleStatus.objects.get_or_create(
            ward=ward, year=year, month=month, schedule_type=schedule_type,
            defaults={'status': ScheduleStatus.DRAFT}
        )
        return status_obj

    @staticmethod
    def get_status(ward, year, month, schedule_type='main'):
        """
        دریافت وضعیت فعلی.
        اولویت: FinalSchedule > MonthlyScheduleStatus > DRAFT
        """
        month_prefix = f"{year}-{str(month).zfill(2)}"
        first_fs = FinalSchedule.objects.filter(
            ward=ward,
            schedule_date__startswith=month_prefix,
            schedule_type=schedule_type
        ).first()

        if first_fs:
            return first_fs.status

        status_obj = MonthlyScheduleStatus.objects.filter(
            ward=ward, year=year, month=month, schedule_type=schedule_type
        ).first()

        if status_obj:
            return status_obj.status

        return ScheduleStatus.DRAFT

    # ========================================================
    # ✅ بررسی امکان تولید
    # ========================================================
    @staticmethod
    def can_generate(ward, year, month, schedule_type='main'):
        """
        بررسی امکان تولید برنامه.
        خروجی: (can_generate, error_message, missing_prerequisite)
        """
        if schedule_type not in WorkflowEngine.DEPENDENCY_RULES:
            return False, f"نوع برنامه '{schedule_type}' نامعتبر است.", None

        rule = WorkflowEngine.DEPENDENCY_RULES[schedule_type]

        # چک پیش‌نیازها
        for required_type, allowed_statuses in rule['requires']:
            required_status = WorkflowEngine.get_status(ward, year, month, required_type)

            if required_status not in allowed_statuses:
                required_label = schedule_type_label(required_type)
                current_label = STATUS_LABELS_FA.get(required_status, required_status)
                this_label = schedule_type_label(schedule_type)

                error_msg = (
                    f"برای تولید برنامه {this_label}، ابتدا باید برنامه "
                    f"{required_label} توسط سرپرستار تایید و به سوپروایزر ارسال شود. "
                    f"وضعیت فعلی برنامه {required_label}: {current_label}"
                )
                return False, error_msg, required_type        # چک وضعیت خودِ این برنامه
        current_status = WorkflowEngine.get_status(ward, year, month, schedule_type)

        if current_status not in rule['can_generate_in_statuses']:
            current_label = STATUS_LABELS_FA.get(current_status, current_status)
            this_label = schedule_type_label(schedule_type)

            error_msg = (
                f"برنامه {this_label} در وضعیت '{current_label}' "
                f"قابل تولید نیست. برای تولید مجدد، باید برنامه به حالت "
                f"«پیش‌نویس» یا «بازگشته به سرپرستار» باشد."
            )
            return False, error_msg, None

        return True, None, None

    # ========================================================
    # جدول انتقال وضعیت‌ها
    # ========================================================
    @staticmethod
    def get_transition_table():
        return {
            ScheduleStatus.DRAFT: {
                'head_approve': ScheduleStatus.PENDING_SUPERVISOR,
                'head_edit': ScheduleStatus.DRAFT,
            },
            ScheduleStatus.PENDING_SUPERVISOR: {
                'supervisor_approve': ScheduleStatus.PENDING_MATRON,
                'supervisor_reject': ScheduleStatus.RETURNED_TO_HEAD,
            },
            ScheduleStatus.PENDING_MATRON: {
                'admin_approve': ScheduleStatus.LOCKED,
                'admin_reject': ScheduleStatus.RETURNED_TO_SUPERVISOR,
            },
            ScheduleStatus.RETURNED_TO_HEAD: {
                'head_approve': ScheduleStatus.PENDING_SUPERVISOR,
                'head_edit': ScheduleStatus.RETURNED_TO_HEAD,
            },
            ScheduleStatus.RETURNED_TO_SUPERVISOR: {
                'supervisor_approve': ScheduleStatus.PENDING_MATRON,
                'supervisor_reject': ScheduleStatus.RETURNED_TO_HEAD,
            },
            ScheduleStatus.LOCKED: {
                'admin_reset': ScheduleStatus.DRAFT,
            },
        }