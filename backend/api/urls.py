# api/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import TransitionStatusView, MonthlyStatusView, MonthlyReportView  # ✅ MonthlyReportView اضافه شد

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'wards', views.WardViewSet)
router.register(r'profiles', views.ProfileViewSet)
router.register(r'shift-requests', views.ShiftRequestViewSet)

urlpatterns = [
    # مسیرهای لاگین JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('my-wards/', views.get_my_wards, name='my-wards'),
    path('my-previous-schedules-wards/', views.get_my_previous_schedules_wards, name='my-previous-schedules-wards'),

    path('monthly', views.get_monthly_calendar, name='monthly_calendar_no_slash'),
    path('monthly/', views.get_monthly_calendar, name='monthly_calendar'),

    path('announcements/', views.AnnouncementListView.as_view(), name='announcements'),

    path('head-schedule/', views.HeadScheduleViewSet.as_view({'get': 'list'}), name='head-schedule'),

    path('final-schedules/', views.FinalScheduleViewSet.as_view({'get': 'list', 'post': 'create'}), name='final-schedules'),

    path('shift-codes/', views.get_shift_codes, name='shift-codes'),

    path('supervisor-schedule/', views.FinalScheduleViewSet.as_view({'get': 'supervisor_schedule'}), name='supervisor-schedule'),
    path('matron-schedule/', views.FinalScheduleViewSet.as_view({'get': 'matron_schedule'}), name='matron-schedule'),

    path('supervisor/approve/', views.FinalScheduleViewSet.as_view({'post': 'approve_all_supervisor'}), name='approve-all-supervisor'),
    path('supervisor/return/', views.FinalScheduleViewSet.as_view({'post': 'return_all_supervisor'}), name='return-all-supervisor'),
    path('head/confirm/', views.FinalScheduleViewSet.as_view({'post': 'approve_all_head'}), name='approve-all-head'),
    path('matron/approve/', views.FinalScheduleViewSet.as_view({'post': 'approve_all_matron'}), name='approve-all-matron'),
    path('matron/return/', views.FinalScheduleViewSet.as_view({'post': 'return_all_to_supervisor'}), name='return-all-to-supervisor'),
    path('matron/reset/', views.FinalScheduleViewSet.as_view({'post': 'reset_all_schedule'}), name='reset-all-schedule'),

    path('save-schedule/', views.save_schedule, name='save-schedule'),
    path('finalize-schedule/', views.finalize_schedule, name='finalize-schedule'),

    path('supervisor-dashboard/', views.FinalScheduleViewSet.as_view({'get': 'supervisor_dashboard'}), name='supervisor-dashboard'),
    path('matron-dashboard/', views.FinalScheduleViewSet.as_view({'get': 'matron_dashboard'}), name='matron-dashboard'),

    # ✅ گردش کار
    path('transition-status/', TransitionStatusView.as_view(), name='transition-status'),

    # ✅ وضعیت هر سه برنامه
    path('monthly-status/', MonthlyStatusView.as_view(), name='monthly-status'),

    # ✅ جدید: گزارش تجمیعی سه برنامه
    path('monthly-report/', MonthlyReportView.as_view(), name='monthly-report'),

    path('export-excel/', views.export_excel, name='export-excel'),
    path('export-pdf/', views.export_pdf, name='export-pdf'),

    path('ai/', include('ai_module.urls')),

    path('site-settings/', views.get_site_settings, name='site-settings'),

    path('my-supervised-wards/', views.get_my_supervised_wards, name='my-supervised-wards'),
    path('all-wards-for-matron/', views.get_all_wards_for_matron, name='all-wards-for-matron'),

    path('change-password/', views.change_password, name='change-password'),
    path('upload-avatar/', views.upload_avatar, name='upload-avatar'),

   # api/urls.py — در urlpatterns اضافه کنید
    # ✅ آپلود اکسل
    path('excel-uploads/download-template/', views.download_excel_template, name='excel-download-template'),
    path('excel-uploads/upload/', views.ExcelUploadView.as_view(), name='excel-upload'),
    path('excel-uploads/history/', views.ExcelUploadHistoryView.as_view(), name='excel-upload-history'),

        # ✅ مدیریت پرسنل برنامه
    path('ai/ward-staff/', views.get_ward_staff_with_overrides, name='ward-staff'),
    path('ai/exclude-staff/', views.exclude_staff_from_schedule, name='exclude-staff'),
    path('ai/restore-staff/', views.restore_staff_to_schedule, name='restore-staff'),
]

urlpatterns += router.urls