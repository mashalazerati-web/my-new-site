# ai_module/urls.py
from django.urls import path
from .views import (
    AIRuleListView,
    AIRuleToggleView,
    AIGenerateScheduleView,
    AIGetScheduleView,
    AICopyToMainScheduleView,
    AICalculateMatchView,
    AICompareSolversView,
    AIGetWardsView,
    AIGetSpecialConfigView,
    AISpecialConfigView,  # ✅ جدید
)

urlpatterns = [
    path('rules/', AIRuleListView.as_view(), name='ai-rules-list'),
    path('rules/toggle/', AIRuleToggleView.as_view(), name='ai-rules-toggle'),
    path('generate/', AIGenerateScheduleView.as_view(), name='ai-generate'),
    path('schedule/', AIGetScheduleView.as_view(), name='ai-schedule-get'),
    path('copy-to-main/', AICopyToMainScheduleView.as_view(), name='ai-copy-to-main'),
    path('calculate-match/', AICalculateMatchView.as_view(), name='ai-calculate-match'),
    path('compare-solvers/', AICompareSolversView.as_view(), name='ai-compare-solvers'),
    path('wards/', AIGetWardsView.as_view(), name='ai-wards'),
    path('special-config/', AIGetSpecialConfigView.as_view(), name='ai-special-config'),
    path('special-config/save/', AISpecialConfigView.as_view(), name='ai-special-config-save'),  # ✅ جدید
]