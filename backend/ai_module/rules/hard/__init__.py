# ai_module/rules/hard/__init__.py
from .max_consecutive_nights import MaxConsecutiveNights
from .no_work_after_night import NoWorkAfterNight
from .minimum_staff_coverage import MinimumStaffCoverage
from .main_schedule_required import MainScheduleRequired

__all__ = [
    'MaxConsecutiveNights',
    'NoWorkAfterNight',
    'MinimumStaffCoverage',
    'MainScheduleRequired',
]