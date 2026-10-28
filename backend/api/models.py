# api/models.py
from django.db import models
from django.contrib.auth.models import User


class ScheduleStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'پیش‌نویس'
    PENDING_HEAD = 'PENDING_HEAD', 'در انتظار تایید سرپرستار'
    PENDING_SUPERVISOR = 'PENDING_SUPERVISOR', 'در انتظار تایید سوپروایزر'
    PENDING_MATRON = 'PENDING_MATRON', 'در انتظار تایید مترون'
    LOCKED = 'LOCKED', 'قفل شده'
    RETURNED_TO_HEAD = 'RETURNED_TO_HEAD', 'بازگشت به سرپرستار'
    RETURNED_TO_SUPERVISOR = 'RETURNED_TO_SUPERVISOR', 'بازگشت به سوپروایزر'


# ✅ انواع برنامه‌ها — منبع واحد
SCHEDULE_TYPE_CHOICES = [
    ('main', 'برنامه اصلی'),
    ('oncall', 'برنامه آنکالی'),
    ('crisis', 'برنامه بحران'),
    ('assistant', 'برنامه کمک پرستار'),
]


class ShiftCode(models.Model):
    code = models.CharField(max_length=10, unique=True, verbose_name="کد شیفت (مثلاً M, N, MfE)")
    label = models.CharField(max_length=100, verbose_name="نام نمایشی (مثلاً صبح)")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.label}"

    class Meta:
        ordering = ['code']
        verbose_name = "کد شیفت"
        verbose_name_plural = "کدهای شیفت"


class SiteSettings(models.Model):
    name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="نام تنظیمات",
        help_text="مثلاً: تنظیمات اصلی، تنظیمات سال ۱۴۰۵، ..."
    )
    university_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="نام دانشگاه")
    university_logo = models.ImageField(upload_to='logos/', blank=True, null=True, verbose_name="آرم دانشگاه")
    hospital_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="نام بیمارستان")
    hospital_logo = models.ImageField(upload_to='logos/', blank=True, null=True, verbose_name="آرم بیمارستان")
    login_background = models.ImageField(upload_to='backgrounds/', blank=True, null=True, verbose_name="تصویر پس‌زمینه صفحه ورود")
    footer_text = models.CharField(max_length=500, blank=True, null=True, verbose_name="متن پاورقی")

    is_active = models.BooleanField(default=False, verbose_name="فعال")

    def __str__(self):
        return self.name or "تنظیمات سراسری سایت"

    def save(self, *args, **kwargs):
        if self.is_active:
            SiteSettings.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"


class Ward(models.Model):
    name = models.CharField(max_length=100, unique=True)
    min_staff_morning = models.IntegerField(default=4)
    min_staff_evening = models.IntegerField(default=4)
    min_staff_night = models.IntegerField(default=4)

    active_shift_codes = models.ManyToManyField(ShiftCode, blank=True, verbose_name="کدهای فعال بخش")

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_wards',
        verbose_name="بخش اصلی (والد)"
    )

    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_wards',
        limit_choices_to={'profile__role': 'supervisor'}
    )

    holiday_min_staff_morning = models.IntegerField(default=1, verbose_name="حداقل پرسنل صبح در روز تعطیل")
    holiday_min_staff_evening = models.IntegerField(default=1, verbose_name="حداقل پرسنل عصر در روز تعطیل")
    holiday_min_staff_night = models.IntegerField(default=1, verbose_name="حداقل پرسنل شب در روز تعطیل")

    sub_ward_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="نام ریز بخش")

    def __str__(self):
        return self.name

    def get_head_name(self):
        try:
            head_profile = Profile.objects.get(ward=self, role='head')
            return f"{head_profile.user.first_name} {head_profile.user.last_name}"
        except Profile.DoesNotExist:
            return "تعیین نشده"

    def get_sub_wards(self):
        return self.sub_wards.all()


class Profile(models.Model):
    ROLE_CHOICES = [
        ('staff', 'پرستار'),
        ('head', 'سرپرستار'),
        ('supervisor', 'سوپروایزر'),
        ('admin', 'مدیر پرستاری (مترون)'),
    ]

    # ✅ دسته پرسنل — برای تفکیک پرستار از کمک پرستار
    STAFF_CATEGORY_CHOICES = [
        ('nurse', 'پرستار'),
        ('assistant', 'کمک پرستار'),
    ]

    # ============================================================
    # ✅ POSITION_CHOICES — نسخه یکتا
    # هر پوزیشن یک کد یکتا دارد
    # ============================================================
    POSITION_CHOICES = [
        ('1', 'مترون'),
        ('2', 'جانشین مترون'),
        ('3', 'سوپروایزر بالینی'),
        ('4', 'سرپرستار / مسئول بخش'),
        ('5', 'سوپروایزر بخش'),
        ('6', 'کارشناس خبره و جانشین 1'),
        ('7', 'کارشناس خبره و جانشین 2'),
        ('8', 'پرستار'),
        ('9', 'ماما'),
        ('10', 'کارشناس آموزش شیردهی'),
        ('11', 'کارشناس / کاردان اتاق عمل'),
        ('12', 'بهیار'),
        ('13', 'کمک پرستار / کمک بهیار'),
        ('14', 'نگهبانی'),
        ('15', 'اینترنشیپ'),
        ('16', 'کارشناس / کاردان بخش'),
        ('17', 'پشتیبانی'),
        ('18', 'خدمات'),
        ('19', 'کارشناس بحران'),
        ('20', 'رابط ایمنی دفتر پرستاری'),
    ]

    EMPLOYMENT_STATUS_CHOICES = [
        ('رسمی', 'رسمی'),
        ('پیمانی', 'پیمانی'),
        ('قراردادی', 'قراردادی'),
        ('شرکتی', 'شرکتی'),
        ('طرحی', 'طرحی'),
    ]

    SHIFT_TYPE_CHOICES = [
        ('سه_نوبتی', 'سه نوبتی'),
        ('ثابت_صبح', 'ثابت صبح'),
        ('ثابت_عصر', 'ثابت عصر'),
        ('ثابت_شب', 'ثابت شب'),
        ('دو_نوبتی_عصر_شب', 'دو نوبتی (عصر-شب)'),
        ('دو_نوبتی_صبح_شب', 'دو نوبتی (صبح-شب)'),
        ('دو_نوبتی_صبح_عصر', 'دو نوبتی (صبح-عصر)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')

    # ✅ دسته پرسنل (پرستار / کمک پرستار)
    staff_category = models.CharField(
        max_length=20,
        choices=STAFF_CATEGORY_CHOICES,
        default='nurse',
        verbose_name="دسته پرسنل",
        help_text="برای برنامه اصلی/آنکالی/بحران از «پرستار» و برای برنامه کمک پرستار از «کمک پرستار» استفاده کنید."
    )

    ward = models.ForeignKey(
        Ward,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles',
        verbose_name="بخش اصلی"
    )
    additional_wards = models.ManyToManyField(
        Ward,
        blank=True,
        related_name='additional_profiles',
        verbose_name="بخش‌های اضافی"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name="عکس پروفایل"
    )

    position = models.CharField(
        max_length=50,
        choices=POSITION_CHOICES,
        default='8',
        blank=True,
        verbose_name="سمت"
    )
    work_experience = models.IntegerField(default=0, verbose_name="سابقه کار (سال)")

    employment_status = models.CharField(max_length=50, choices=EMPLOYMENT_STATUS_CHOICES, default='رسمی', blank=True)
    shift_type = models.CharField(max_length=50, choices=SHIFT_TYPE_CHOICES, default='سه_نوبتی', blank=True)
    signature = models.ImageField(upload_to='signatures/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def is_assistant(self):
        return self.staff_category == 'assistant'

    def is_nurse(self):
        return self.staff_category == 'nurse'

    def get_position_display(self):
        """
        ✅ نمایش سمت — با اولویت staff_category.
        اگر کاربر «کمک پرستار» است، صرف‌نظر از position، «کمک پرستار» نمایش بده.
        """
        if self.staff_category == 'assistant':
            return 'کمک پرستار'
        # ✅ خودمون از POSITION_CHOICES استفاده می‌کنیم (چون super() نداره)
        return dict(self.POSITION_CHOICES).get(self.position, self.position or '')
        
    class Meta:
        verbose_name = "پروفایل"
        verbose_name_plural = "پروفایل‌ها"


class ShiftRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE)
    request_date = models.CharField(max_length=10)
    shift_code = models.ForeignKey(ShiftCode, on_delete=models.PROTECT, null=True, blank=False)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.first_name} - {self.request_date}"

    class Meta:
        verbose_name = "درخواست شیفت"
        verbose_name_plural = "درخواست‌های شیفت"


class FinalSchedule(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE)
    schedule_date = models.CharField(max_length=10)
    shift_code = models.ForeignKey(ShiftCode, on_delete=models.PROTECT, null=True, blank=False)
    assigned_staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='final_schedules')

    is_locked = models.BooleanField(default=False)
    approved_by_head = models.BooleanField(default=False)
    approved_by_supervisor = models.BooleanField(default=False)
    approved_by_matron = models.BooleanField(default=False)
    returned_to_head = models.BooleanField(default=False, verbose_name="بازگردانده شده به سرپرستار")

    matron_feedback = models.TextField(blank=True, null=True, verbose_name="نظر مترون")
    supervisor_feedback = models.TextField(blank=True, null=True, verbose_name="نظر سوپروایزر")
    ward_notes = models.TextField(blank=True, null=True, verbose_name="نکات مهم بخش")

    status = models.CharField(
        max_length=30,
        choices=ScheduleStatus.choices,
        default=ScheduleStatus.DRAFT,
        verbose_name="وضعیت"
    )

    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPE_CHOICES,
        default='main',
        verbose_name="نوع برنامه"
    )

    def __str__(self):
        return f"{self.ward} - {self.schedule_date}"

    def apply_status(self, new_status):
        self.status = new_status
        self.approved_by_head = new_status in (
            ScheduleStatus.PENDING_SUPERVISOR,
            ScheduleStatus.PENDING_MATRON,
            ScheduleStatus.LOCKED,
        )
        self.approved_by_supervisor = new_status in (
            ScheduleStatus.PENDING_MATRON,
            ScheduleStatus.LOCKED,
        )
        self.approved_by_matron = new_status == ScheduleStatus.LOCKED
        self.is_locked = new_status == ScheduleStatus.LOCKED
        self.returned_to_head = new_status == ScheduleStatus.RETURNED_TO_HEAD

    def get_approval_status(self):
        if self.is_locked:
            return 'locked'
        elif self.returned_to_head:
            return 'returned_to_head'
        elif self.approved_by_matron:
            return 'approved_by_matron'
        elif self.approved_by_supervisor:
            return 'approved_by_supervisor'
        elif self.approved_by_head:
            return 'approved_by_head'
        else:
            return 'pending'

    def get_approval_status_display(self):
        status_map = {
            'locked': '✅ تأیید نهایی و قفل شده',
            'returned_to_head': '🔄 بازگردانده شده به سرپرستار (با توضیحات)',
            'approved_by_matron': '✅ تأیید مترون - در انتظار قفل شدن',
            'approved_by_supervisor': '✅ تأیید سوپروایزر - در انتظار مترون',
            'approved_by_head': '⏳ تأیید سرپرستار - در انتظار سوپروایزر',
            'pending': '⏳ در انتظار تأیید سرپرستار'
        }
        return status_map.get(self.get_approval_status(), 'نامشخص')

    class Meta:
        verbose_name = "برنامه نهایی"
        verbose_name_plural = "برنامه‌های نهایی"


class DraftSchedule(models.Model):
    """برنامه پیش‌نویس سرپرستار (دستی یا هوش مصنوعی)"""
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE)
    schedule_date = models.CharField(max_length=10)
    shift_code = models.ForeignKey(ShiftCode, on_delete=models.PROTECT, null=True, blank=False)
    assigned_staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='draft_schedules')
    source = models.CharField(max_length=20, choices=[
        ('manual', 'دستی سرپرستار'),
        ('ai', 'هوش مصنوعی')
    ], default='manual')

    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPE_CHOICES,
        default='main',
        verbose_name="نوع برنامه"
    )

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_drafts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ward} - {self.schedule_date} - {self.assigned_staff}"

    class Meta:
        verbose_name = "برنامه پیش‌نویس"
        verbose_name_plural = "برنامه‌های پیش‌نویس"


# ============================================================
# Announcement
# ============================================================
class Announcement(models.Model):
    PRIORITY_CHOICES = [
        ('normal', 'عادی'),
        ('important', 'مهم'),
        ('urgent', 'فوری'),
    ]

    title = models.CharField(max_length=200, verbose_name="عنوان")
    content = models.TextField(verbose_name="متن خبر/دستورالعمل")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name="اهمیت"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_announcements',
        verbose_name="ایجاد شده توسط"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_announcements',
        verbose_name="آخرین ویرایش توسط"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخرین ویرایش"
    )

    is_edited = models.BooleanField(
        default=False,
        verbose_name="ویرایش شده",
        help_text="اگر True باشد، به کاربر نمایش داده می‌شود که این خبر ویرایش شده است"
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.pk:
            self.is_edited = True
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "اخبار و دستورالعمل"
        verbose_name_plural = "اخبار و دستورالعمل‌ها"
        ordering = ['-created_at']


class AnnouncementAttachment(models.Model):
    ATTACHMENT_TYPES = [
        ('image', 'تصویر'),
        ('video', 'فیلم'),
        ('pdf', 'PDF'),
        ('file', 'فایل'),
    ]

    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name="خبر"
    )
    file = models.FileField(
        upload_to='announcements/%Y/%m/',
        verbose_name="فایل"
    )
    file_type = models.CharField(
        max_length=20,
        choices=ATTACHMENT_TYPES,
        verbose_name="نوع فایل"
    )
    caption = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        verbose_name="توضیح"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "ضمیمه خبر"
        verbose_name_plural = "ضمیمه‌های خبر"

    def __str__(self):
        return f"{self.announcement.title} - {self.get_file_type_display()}"


class Holiday(models.Model):
    date = models.CharField(max_length=10, unique=True, verbose_name="تاریخ (YYYY-MM-DD)")
    name = models.CharField(max_length=100, verbose_name="نام تعطیلات")
    year = models.IntegerField(verbose_name="سال")

    def __str__(self):
        return f"{self.date} - {self.name}"

    class Meta:
        verbose_name = "تعطیلات"
        verbose_name_plural = "تعطیلات"
        ordering = ['date']


class WardMonthlyNotes(models.Model):
    """نکات مهم بخش برای یک ماه خاص"""
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='monthly_notes')
    year = models.IntegerField(verbose_name="سال شمسی")
    month = models.IntegerField(verbose_name="ماه شمسی")
    notes = models.TextField(blank=True, null=True, verbose_name="نکات مهم بخش")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('ward', 'year', 'month')
        verbose_name = "نکات ماهانه بخش"
        verbose_name_plural = "نکات ماهانه بخش‌ها"

    def __str__(self):
        return f"{self.ward.name} - {self.year}/{self.month}"


class MonthlyScheduleStatus(models.Model):
    """
    وضعیت مستقل هر نوع برنامه برای یک بخش در یک ماه.
    """
    ward = models.ForeignKey(
        Ward,
        on_delete=models.CASCADE,
        related_name='monthly_statuses',
        verbose_name="بخش"
    )
    year = models.IntegerField(verbose_name="سال شمسی")
    month = models.IntegerField(verbose_name="ماه شمسی")
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPE_CHOICES,
        default='main',
        verbose_name="نوع برنامه"
    )
    status = models.CharField(
        max_length=30,
        choices=ScheduleStatus.choices,
        default=ScheduleStatus.DRAFT,
        verbose_name="وضعیت"
    )

    ward_notes = models.TextField(blank=True, null=True, verbose_name="نکات مهم بخش")
    supervisor_feedback = models.TextField(blank=True, null=True, verbose_name="نظر سوپروایزر")
    matron_feedback = models.TextField(blank=True, null=True, verbose_name="نظر مترون")

    head_signature = models.ImageField(
        upload_to='schedule_signatures/head/',
        blank=True, null=True,
        verbose_name="امضای سرپرستار (این برنامه)"
    )
    supervisor_signature = models.ImageField(
        upload_to='schedule_signatures/supervisor/',
        blank=True, null=True,
        verbose_name="امضای سوپروایزر (این برنامه)"
    )
    matron_signature = models.ImageField(
        upload_to='schedule_signatures/matron/',
        blank=True, null=True,
        verbose_name="امضای مترون (این برنامه)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='updated_schedule_statuses',
        verbose_name="آخرین ویرایش‌کننده"
    )

    def __str__(self):
        return f"[{self.get_schedule_type_display()}] {self.ward.name} - {self.year}/{self.month} - {self.status}"

    class Meta:
        unique_together = ('ward', 'year', 'month', 'schedule_type')
        verbose_name = "وضعیت برنامه ماهانه"
        verbose_name_plural = "وضعیت‌های برنامه‌های ماهانه"
        ordering = ['-year', '-month', 'ward__name', 'schedule_type']
        indexes = [
            models.Index(fields=['ward', 'year', 'month', 'schedule_type']),
            models.Index(fields=['status']),
        ]

    def apply_status(self, new_status):
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])

    def is_editable(self, user_role='head'):
        return (
            user_role == 'head'
            and self.status in [ScheduleStatus.DRAFT, ScheduleStatus.RETURNED_TO_HEAD]
        )

    def is_locked(self):
        return self.status == ScheduleStatus.LOCKED

    def get_status_display_persian(self):
        return {
            ScheduleStatus.DRAFT: '⏳ پیش‌نویس',
            ScheduleStatus.PENDING_SUPERVISOR: '⏳ در انتظار تایید سوپروایزر',
            ScheduleStatus.PENDING_MATRON: '⏳ در انتظار تایید نهایی مترون',
            ScheduleStatus.LOCKED: '🔒 قفل شده',
            ScheduleStatus.RETURNED_TO_HEAD: '🔄 بازگشته به سرپرستار',
            ScheduleStatus.RETURNED_TO_SUPERVISOR: '🔄 بازگشته به سوپروایزر',
        }.get(self.status, 'نامشخص')


class ExcelUpload(models.Model):
    """آپلود فایل اکسل برای ورود گروهی اطلاعات"""

    STATUS_CHOICES = [
        ('pending', 'در انتظار پردازش'),
        ('processing', 'در حال پردازش'),
        ('success', 'موفق'),
        ('partial', 'موفق با خطا'),
        ('failed', 'ناموفق'),
    ]

    file = models.FileField(
        upload_to='excel_uploads/%Y/%m/',
        verbose_name="فایل اکسل"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="وضعیت"
    )
    result_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="نتیجه پردازش"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="پیام خطا"
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="آپلود شده توسط"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پردازش")

    class Meta:
        verbose_name = "آپلود اکسل"
        verbose_name_plural = "آپلودهای اکسل"
        ordering = ['-created_at']

    def __str__(self):
        return f"آپلود #{self.id} - {self.get_status_display()}"


class ScheduleStaffOverride(models.Model):
    """
    تنظیمات موقت سرپرستار برای حذف پرسنل از یک برنامه خاص.
    """
    ward = models.ForeignKey(
        Ward,
        on_delete=models.CASCADE,
        related_name='staff_overrides',
        verbose_name="بخش"
    )
    year = models.IntegerField(verbose_name="سال شمسی")
    month = models.IntegerField(verbose_name="ماه شمسی")
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPE_CHOICES,
        default='main',
        verbose_name="نوع برنامه"
    )

    staff = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='schedule_overrides',
        verbose_name="پرسنل"
    )

    reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="دلیل حذف",
        help_text="دلیل حذف موقت پرستار از برنامه"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_overrides',
        verbose_name="ایجاد شده توسط"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('ward', 'year', 'month', 'schedule_type', 'staff')
        verbose_name = "حذف موقت پرسنل"
        verbose_name_plural = "حذف‌های موقت پرسنل"

    def __str__(self):
        return f"{self.staff.username} - {self.year}/{self.month} - {self.schedule_type}"