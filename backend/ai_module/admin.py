# ai_module/admin.py
from django.contrib import admin
from .models import AIRule, AIPrompt, AISchedule, SpecialScheduleConfig


@admin.register(AIRule)
class AIRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'schedule_type', 'is_active', 'created_at')
    list_filter = ('schedule_type', 'is_active')
    search_fields = ('name', 'description')
    list_editable = ('is_active',)


@admin.register(AIPrompt)
class AIPromptAdmin(admin.ModelAdmin):
    list_display = ('user', 'prompt_text', 'created_at')
    search_fields = ('prompt_text',)


@admin.register(AISchedule)
class AIScheduleAdmin(admin.ModelAdmin):
    list_display = ('ward', 'year', 'month', 'schedule_type', 'status', 'created_at')
    list_filter = ('status', 'schedule_type', 'ward', 'year')


@admin.register(SpecialScheduleConfig)
class SpecialScheduleConfigAdmin(admin.ModelAdmin):
    list_display = (
        'ward',
        'schedule_type',
        'min_staff_morning',
        'min_staff_evening',
        'min_staff_night',
        'holiday_min_staff_morning',
        'holiday_min_staff_evening',
        'holiday_min_staff_night',
    )
    list_filter = ('schedule_type', 'ward')
    search_fields = ('ward__name',)
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('ward', 'schedule_type')
        }),
        ('چینش روزهای عادی', {
            'fields': (
                'min_staff_morning',
                'min_staff_evening',
                'min_staff_night',
            )
        }),
        ('چینش روزهای تعطیل', {
            'fields': (
                'holiday_min_staff_morning',
                'holiday_min_staff_evening',
                'holiday_min_staff_night',
            )
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
    )