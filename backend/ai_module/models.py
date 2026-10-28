# ai_module/models.py
from django.db import models
from django.contrib.auth.models import User
from api.models import Ward, SCHEDULE_TYPE_CHOICES


# ✅ choices مشترک برای انواع برنامه (شامل assistant)
AI_SCHEDULE_TYPE_CHOICES = [
    ('main', 'برنامه اصلی'),
    ('oncall', 'برنامه آنکالی'),
    ('crisis', 'برنامه بحران'),
    ('assistant', 'برنامه کمک پرستار'),  # ✅ جدید
]


class AIRule(models.Model):
    """مدل ذخیره قوانین هوش مصنوعی"""
    schedule_type = models.CharField(
        max_length=20,
        choices=AI_SCHEDULE_TYPE_CHOICES,   # ✅ شامل assistant
        default='main',
        verbose_name="نوع برنامه"
    )
    name = models.CharField(max_length=200, verbose_name="نام قانون")
    description = models.TextField(verbose_name="توضیحات قانون", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    logic_code = models.TextField(blank=True, null=True, verbose_name="کد منطق قانون")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_schedule_type_display()}] {self.name} - {'فعال' if self.is_active else 'غیرفعال'}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "قانون هوش مصنوعی"
        verbose_name_plural = "قوانین هوش مصنوعی"


class AIPrompt(models.Model):
    """مدل ذخیره پرامپت‌های کاربر"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_prompts')
    prompt_text = models.TextField(verbose_name="متن پرامپت")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"پرامپت توسط {self.user.username} در {self.created_at}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "پرامپت هوش مصنوعی"
        verbose_name_plural = "پرامپت‌های هوش مصنوعی"


class AISchedule(models.Model):
    """مدل ذخیره برنامه پیشنهادی"""
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('generated', 'تولید شده'),
        ('reviewed', 'بررسی شده'),
        ('ready_to_copy', 'آماده برای کپی'),
    ]

    schedule_type = models.CharField(
        max_length=20,
        choices=AI_SCHEDULE_TYPE_CHOICES,   # ✅ شامل assistant
        default='main',
        verbose_name="نوع برنامه"
    )
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='ai_schedules')
    year = models.IntegerField(verbose_name="سال شمسی")
    month = models.IntegerField(verbose_name="ماه شمسی")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")
    ai_generated_data = models.JSONField(default=dict, verbose_name="داده‌های برنامه")
    related_prompt = models.ForeignKey(AIPrompt, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_schedules')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_schedule_type_display()}] {self.ward.name} - {self.year}/{self.month}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "برنامه هوش مصنوعی"
        verbose_name_plural = "برنامه‌های هوش مصنوعی"
        unique_together = ('ward', 'year', 'month', 'schedule_type')


class SpecialScheduleConfig(models.Model):
    """
    تنظیمات چینش استاندارد برنامه‌های آنکالی، بحران و کمک پرستار.
    برای هر بخش، یک رکورد برای هر نوع برنامه ذخیره می‌شود.
    تفکیک صبح/عصر/شب برای روزهای عادی و تعطیل.
    """
    SCHEDULE_TYPE_CHOICES = [
        ('oncall', 'آنکالی'),
        ('crisis', 'بحران'),
        ('assistant', 'کمک پرستار'),   # ✅ جدید
    ]

    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPE_CHOICES,
        verbose_name="نوع برنامه"
    )
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='special_schedule_configs')

    # ✅ حداقل پرسنل در روزهای عادی
    min_staff_morning = models.IntegerField(default=1, verbose_name="حداقل پرسنل صبح (عادی)")
    min_staff_evening = models.IntegerField(default=1, verbose_name="حداقل پرسنل عصر (عادی)")
    min_staff_night = models.IntegerField(default=1, verbose_name="حداقل پرسنل شب (عادی)")

    # ✅ حداقل پرسنل در روزهای تعطیل
    holiday_min_staff_morning = models.IntegerField(default=1, verbose_name="حداقل پرسنل صبح (تعطیل)")
    holiday_min_staff_evening = models.IntegerField(default=1, verbose_name="حداقل پرسنل عصر (تعطیل)")
    holiday_min_staff_night = models.IntegerField(default=1, verbose_name="حداقل پرسنل شب (تعطیل)")

    # ✅ توضیحات
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_schedule_type_display()}] {self.ward.name}"

    class Meta:
        unique_together = ('ward', 'schedule_type')
        verbose_name = "تنظیمات چینش آنکالی/بحران/کمک پرستار"
        verbose_name_plural = "تنظیمات چینش آنکالی/بحران/کمک پرستار"