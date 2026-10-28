# api/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Ward, Profile, ShiftRequest, FinalSchedule,
    Announcement, ShiftCode, SiteSettings, DraftSchedule
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


# api/serializers.py

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    position_label = serializers.SerializerMethodField()
    staff_category_label = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'id', 'user', 'role', 'ward', 'employment_status',
            'shift_type', 'signature', 'avatar', 'avatar_url',
            'position', 'position_label',
            'staff_category', 'staff_category_label',
        ]

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def get_position_label(self, obj):
        """✅ نمایش صحیح سمت — با استفاده از override در مدل"""
        return obj.get_position_display()

    def get_staff_category_label(self, obj):
        """✅ نمایش فارسی دسته پرسنل"""
        return obj.get_staff_category_display()

        
class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = [
            'id', 'name', 'min_staff_morning', 'min_staff_evening', 'min_staff_night',
            'sub_ward_name', 'holiday_min_staff_morning', 'holiday_min_staff_evening',
            'holiday_min_staff_night'
        ]


class ShiftCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftCode
        fields = ['id', 'code', 'label']


class ShiftRequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    ward = WardSerializer(read_only=True)
    shift_code = ShiftCodeSerializer(read_only=True)

    class Meta:
        model = ShiftRequest
        fields = ['id', 'user', 'ward', 'request_date', 'shift_code', 'is_approved']


class FinalScheduleSerializer(serializers.ModelSerializer):
    ward = WardSerializer(read_only=True)
    assigned_staff = UserSerializer(read_only=True)
    shift_code = ShiftCodeSerializer(read_only=True)

    approval_status = serializers.SerializerMethodField()
    approval_status_display = serializers.SerializerMethodField()
    schedule_type_display = serializers.SerializerMethodField()

    class Meta:
        model = FinalSchedule
        fields = [
            'id',
            'ward',
            'schedule_date',
            'shift_code',
            'assigned_staff',
            'is_locked',
            'approved_by_head',
            'approved_by_supervisor',
            'approved_by_matron',
            'approval_status',
            'approval_status_display',
            'schedule_type',
            'schedule_type_display',
        ]
        read_only_fields = [
            'approved_by_head',
            'approved_by_supervisor',
            'approved_by_matron',
            'is_locked'
        ]

    def get_approval_status(self, obj):
        return obj.get_approval_status()

    def get_approval_status_display(self, obj):
        return obj.get_approval_status_display()

    def get_schedule_type_display(self, obj):
        return obj.get_schedule_type_display()


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            'university_name', 'university_logo',
            'hospital_name', 'hospital_logo',
            'login_background', 'footer_text'
        ]


# api/serializers.py
from .models import Announcement, AnnouncementAttachment


class AnnouncementAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = AnnouncementAttachment
        fields = [
            'id',
            'file_url',
            'file_name',
            'file_size',
            'file_type',
            'caption',
            'order',
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_file_size(self, obj):
        try:
            return obj.file.size
        except (ValueError, OSError):
            return 0

    def get_file_name(self, obj):
        try:
            return obj.file.name.split('/')[-1]
        except Exception:
            return ''


# api/serializers.py

class AnnouncementSerializer(serializers.ModelSerializer):
    attachments = AnnouncementAttachmentSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id',
            'title',
            'content',
            'is_active',
            'priority',
            'priority_display',
            'created_at',
            'created_by_name',
            'updated_at',
            'updated_by_name',
            'is_edited',
            'attachments',
        ]
        read_only_fields = [
            'created_at',
            'created_by_name',
            'updated_at',
            'updated_by_name',
            'is_edited',
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            full_name = f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
            return full_name or obj.created_by.username
        return 'مدیر سیستم'

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            full_name = f"{obj.updated_by.first_name} {obj.updated_by.last_name}".strip()
            return full_name or obj.updated_by.username
        return None

        
class DraftScheduleSerializer(serializers.ModelSerializer):
    ward = WardSerializer(read_only=True)
    assigned_staff = UserSerializer(read_only=True)
    shift_code = ShiftCodeSerializer(read_only=True)
    schedule_type_display = serializers.SerializerMethodField()

    class Meta:
        model = DraftSchedule
        fields = [
            'id', 'ward', 'schedule_date', 'shift_code',
            'assigned_staff', 'source', 'created_by',
            'schedule_type', 'schedule_type_display',
            'created_at', 'updated_at'
        ]

    def get_schedule_type_display(self, obj):
        return obj.get_schedule_type_display()