# api/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages

from .models import (
    Ward, Profile, ShiftRequest, FinalSchedule, Announcement,
    Holiday, ShiftCode, SiteSettings, DraftSchedule,
    AnnouncementAttachment, ExcelUpload,
)


# ============================================
# ✅ Custom User Admin
# ============================================
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'get_role', 'get_ward')

    def get_role(self, obj):
        try:
            return obj.profile.role
        except Exception:
            return '-'
    get_role.short_description = 'نقش'

    def get_ward(self, obj):
        try:
            wards = []
            if obj.profile.ward:
                wards.append(obj.profile.ward.name)
            for w in obj.profile.additional_wards.all():
                wards.append(w.name)
            return ', '.join(wards) if wards else '-'
        except Exception:
            return '-'
    get_ward.short_description = 'بخش‌ها'


# ============================================
# ✅ Profile Admin
# ============================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'ward', 'get_additional_wards', 'position', 'employment_status')
    list_filter = ('role', 'ward', 'employment_status')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    filter_horizontal = ('additional_wards',)
    list_select_related = ('user', 'ward')

    def get_additional_wards(self, obj):
        wards = obj.additional_wards.all()
        return ', '.join([w.name for w in wards]) if wards else '-'
    get_additional_wards.short_description = 'بخش‌های اضافی'


# ============================================
# ✅ Ward Admin
# ============================================
@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'get_head_name', 'get_staff_count')
    list_filter = ('parent',)
    search_fields = ('name',)
    filter_horizontal = ('active_shift_codes',)

    def get_head_name(self, obj):
        return obj.get_head_name()
    get_head_name.short_description = 'سرپرستار'

    def get_staff_count(self, obj):
        return Profile.objects.filter(ward=obj, role='staff').count()
    get_staff_count.short_description = 'تعداد پرسنل'


# ============================================
# ✅ Shift Request Admin
# ============================================
@admin.register(ShiftRequest)
class ShiftRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'ward', 'request_date', 'shift_code', 'is_approved')
    list_filter = ('ward', 'is_approved', 'request_date')
    search_fields = ('user__first_name', 'user__last_name', 'request_date')
    list_editable = ('is_approved',)
    # ⚠️ date_hierarchy حذف شد (request_date فیلد متنی است)


# ============================================
# ✅ Final Schedule Admin
# ============================================
@admin.register(FinalSchedule)
class FinalScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'ward', 'schedule_date', 'shift_code', 'assigned_staff',
        'status', 'schedule_type', 'is_locked'
    )
    list_filter = ('ward', 'status', 'schedule_type', 'is_locked', 'schedule_date')
    search_fields = (
        'ward__name', 'assigned_staff__first_name',
        'assigned_staff__last_name', 'schedule_date'
    )
    list_select_related = ('ward', 'assigned_staff', 'shift_code')
    # ⚠️ date_hierarchy حذف شد (schedule_date فیلد متنی است)


# ============================================
# ✅ Announcement Admin (با Inline)
# ============================================
class AnnouncementAttachmentInline(admin.TabularInline):
    model = AnnouncementAttachment
    extra = 1
    fields = ('file', 'file_type', 'caption', 'order', 'preview_thumbnail')
    readonly_fields = ('preview_thumbnail',)
    ordering = ('order',)

    def preview_thumbnail(self, obj):
        if not obj.file:
            return mark_safe('-')

        if obj.file_type == 'image':
            html = (
                '<img src="' + obj.file.url + '" '
                'style="max-height: 60px; max-width: 100px; '
                'border-radius: 6px; border: 1px solid #ddd;" />'
            )
            return mark_safe(html)
        else:
            icons = {'video': '🎬', 'pdf': '📄', 'file': '📎'}
            icon = icons.get(obj.file_type, '📎')
            return mark_safe('<span style="font-size: 28px;">' + icon + '</span>')
    preview_thumbnail.short_description = 'پیش‌نمایش'


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'priority_badge', 'is_active',
        'created_at', 'last_update_info', 'attachments_count',
    )
    list_filter = ('is_active', 'priority', 'is_edited', 'created_at')
    search_fields = ('title', 'content')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'updated_by', 'is_edited')
    inlines = [AnnouncementAttachmentInline]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'content', 'priority')
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        }),
        ('تاریخچه', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at', 'is_edited'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            if not obj.created_by:
                obj.created_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def priority_badge(self, obj):
        colors = {
            'normal': ('#E5E7EB', '#374151'),
            'important': ('#FEF3C7', '#92400E'),
            'urgent': ('#FEE2E2', '#991B1B'),
        }
        bg, color = colors.get(obj.priority, colors['normal'])
        labels = {
            'normal': '📢 عادی',
            'important': '⚠️ مهم',
            'urgent': '🚨 فوری',
        }
        label = labels.get(obj.priority, obj.priority or '-')
        return mark_safe(
            '<span style="padding: 3px 10px; border-radius: 12px; '
            'background: ' + bg + '; color: ' + color + '; '
            'font-weight: bold; font-size: 12px;">' + label + '</span>'
        )
    priority_badge.short_description = 'اهمیت'

    def last_update_info(self, obj):
        if not obj.is_edited or not obj.updated_at:
            return mark_safe('<span style="color: #9CA3AF; font-size: 11px;">—</span>')
        try:
            import jdatetime
            jalali = jdatetime.datetime.fromgregorian(datetime=obj.updated_at)
            date_str = jalali.strftime('%Y/%m/%d')
            time_str = jalali.strftime('%H:%M')
        except Exception:
            date_str = obj.updated_at.strftime('%Y-%m-%d')
            time_str = obj.updated_at.strftime('%H:%M')
        return mark_safe(
            '<div style="font-size: 11px; line-height: 1.5;">'
            '<span style="color: #D97706; font-weight: bold;">✏️ ویرایش شده</span><br/>'
            '<span style="color: #6B7280;">' + date_str + ' - ' + time_str + '</span>'
            '</div>'
        )
    last_update_info.short_description = 'آخرین ویرایش'

    def attachments_count(self, obj):
        count = obj.attachments.count()
        if count == 0:
            return mark_safe('<span style="color: #9CA3AF;">—</span>')
        return mark_safe(
            '<span style="padding: 2px 8px; background: #DBEAFE; '
            'color: #1E40AF; border-radius: 10px; '
            'font-weight: bold;">' + str(count) + '</span>'
        )
    attachments_count.short_description = 'تعداد ضمیمه'


@admin.register(AnnouncementAttachment)
class AnnouncementAttachmentAdmin(admin.ModelAdmin):
    list_display = ('announcement', 'file_type', 'caption', 'order', 'created_at')
    list_filter = ('file_type', 'created_at')
    search_fields = ('announcement__title', 'caption')


# ============================================
# ✅ Holiday Admin
# ============================================
@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('date', 'name', 'year')
    list_filter = ('year',)
    search_fields = ('date', 'name')
    ordering = ('-year', 'date')


# ============================================
# ✅ Shift Code Admin
# ============================================
@admin.register(ShiftCode)
class ShiftCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'label', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'label')
    ordering = ('code',)


# ============================================
# ✅ Site Settings Admin
# ============================================
@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'university_name', 'hospital_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'university_name', 'hospital_name')
    list_editable = ('is_active',)
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'university_name', 'university_logo',
                'hospital_name', 'hospital_logo',
                'login_background', 'footer_text',
                'is_active',
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.is_active:
            SiteSettings.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


# ============================================
# ✅ Draft Schedule Admin
# ============================================
@admin.register(DraftSchedule)
class DraftScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'ward', 'schedule_date', 'shift_code', 'assigned_staff',
        'source', 'schedule_type', 'created_at'
    )
    list_filter = ('ward', 'source', 'schedule_type', 'created_at')
    search_fields = (
        'ward__name', 'assigned_staff__first_name',
        'assigned_staff__last_name', 'schedule_date'
    )
    ordering = ('-created_at',)


# ============================================
# ✅ Excel Upload Admin
# ============================================
@admin.register(ExcelUpload)
class ExcelUploadAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'file_link', 'status_badge', 'uploaded_by',
        'created_at', 'processed_at', 'summary_info'
    )
    list_filter = ('status', 'created_at')
    readonly_fields = (
        'status', 'result_data_display', 'uploaded_by',
        'created_at', 'processed_at', 'error_message'
    )
    fieldsets = (
        ('آپلود فایل', {
            'fields': ('file',)
        }),
        ('وضعیت', {
            'fields': ('status', 'uploaded_by', 'created_at', 'processed_at', 'error_message')
        }),
        ('نتیجه پردازش', {
            'fields': ('result_data_display',),
            'classes': ('collapse',)
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'download-template/',
                self.admin_site.admin_view(self.download_template_view),
                name='excel-download-template'
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['download_template_url'] = 'download-template/'
        return super().changelist_view(request, extra_context)

    def download_template_view(self, request):
        """دانلود قالب نمونه"""
        from django.http import FileResponse
        import os
        from django.conf import settings

        template_path = os.path.join(settings.BASE_DIR, 'نمونه_اطلاعات.xlsx')

        if not os.path.exists(template_path):
            try:
                from create_sample_excel import create_sample_excel
                os.chdir(settings.BASE_DIR)
                create_sample_excel()
            except Exception as e:
                messages.error(request, f'خطا در ساخت قالب: {e}')
                return redirect('..')

        if os.path.exists(template_path):
            return FileResponse(
                open(template_path, 'rb'),
                as_attachment=True,
                filename='نمونه_اطلاعات.xlsx'
            )

        messages.error(request, 'قالب نمونه یافت نشد')
        return redirect('..')

    def file_link(self, obj):
        if obj.file:
            return mark_safe(
                f'<a href="{obj.file.url}" target="_blank" '
                f'style="color: #3B82F6; font-weight: bold;">📥 دانلود</a>'
            )
        return '-'
    file_link.short_description = 'فایل'

    def status_badge(self, obj):
        colors = {
            'pending': ('#FEF3C7', '#92400E', '⏳'),
            'processing': ('#DBEAFE', '#1E40AF', '🔄'),
            'success': ('#D1FAE5', '#065F46', '✅'),
            'partial': ('#FED7AA', '#9A3412', '⚠️'),
            'failed': ('#FEE2E2', '#991B1B', '❌'),
        }
        bg, color, icon = colors.get(obj.status, ('#F3F4F6', '#374151', '?'))
        return mark_safe(
            f'<span style="padding: 4px 12px; border-radius: 12px; '
            f'background: {bg}; color: {color}; font-weight: bold;">'
            f'{icon} {obj.get_status_display()}</span>'
        )
    status_badge.short_description = 'وضعیت'

    def summary_info(self, obj):
        if not obj.result_data:
            return '-'
        summary = obj.result_data.get('summary', {})
        created = summary.get('total_created', 0)
        updated = summary.get('total_updated', 0)
        errors = summary.get('total_errors', 0)
        parts = []
        if created:
            parts.append(f'✅ {created} ایجاد')
        if updated:
            parts.append(f'🔄 {updated} به‌روزرسانی')
        if errors:
            parts.append(f'❌ {errors} خطا')
        return mark_safe(' | '.join(parts) if parts else '-')
    summary_info.short_description = 'خلاصه'

    def result_data_display(self, obj):
        if not obj.result_data:
            return '-'
        html = '<div style="direction: rtl; font-family: Tahoma; line-height: 1.8;">'
        sections = {
            'staff': '👥 پرسنل',
            'wards': '🏥 بخش‌ها',
            'holidays': '📅 تعطیلات',
            'shift_codes': '🔧 کدهای شیفت',
        }
        for key, label in sections.items():
            data = obj.result_data.get(key)
            if not data:
                continue
            html += f'<h3 style="color: #1E40AF; margin-top: 15px;">{label}</h3>'
            html += (
                f'<p>'
                f'<b>کل:</b> {data.get("total", 0)} | '
                f'<b style="color: #10B981;">ایجاد:</b> {data.get("created", 0)} | '
                f'<b style="color: #F59E0B;">به‌روزرسانی:</b> {data.get("updated", 0)} | '
                f'<b style="color: #EF4444;">خطا:</b> {len(data.get("errors", []))}'
                f'</p>'
            )
            errors = data.get('errors', [])[:10]
            if errors:
                html += '<details><summary style="cursor: pointer; color: #EF4444;">نمایش خطاها</summary><ul>'
                for err in errors:
                    html += f'<li>ردیف {err.get("row", "?")}: {err.get("message", "")}</li>'
                html += '</ul></details>'
        html += '</div>'
        return mark_safe(html)
    result_data_display.short_description = 'جزئیات نتیجه'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
            obj.status = 'processing'
            super().save_model(request, obj, form, change)

            from .excel_import import process_upload
            process_upload(obj)

            if obj.status == 'success':
                messages.success(request, '✅ فایل با موفقیت پردازش شد!')
            elif obj.status == 'partial':
                messages.warning(request, '⚠️ فایل با برخی خطاها پردازش شد.')
            else:
                messages.error(request, '❌ پردازش فایل ناموفق بود.')
        else:
            super().save_model(request, obj, form, change)


# ============================================
# ✅ Register User with Custom Admin
# ============================================
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)