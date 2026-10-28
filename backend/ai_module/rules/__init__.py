# ai_module/rules/__init__.py
"""
سیستم Rule Engine — صادرات اصلی
"""

from .base import Rule
from .context import ScheduleContext, StaffInfo
from .violations import (
    Violation,
    RuleResult,
    AggregateResult,
    Severity,
    RuleCategory,
)
from .registry import RuleRegistry, get_rule_registry

# Hard rules
from .hard.max_consecutive_nights import MaxConsecutiveNights
from .hard.no_work_after_night import NoWorkAfterNight
from .hard.minimum_staff_coverage import MinimumStaffCoverage
from .hard.main_schedule_required import MainScheduleRequired

# Soft rules
from .soft.preferred_shift import PreferredShiftForStaff
from .soft.fair_distribution import FairShiftDistribution

# Legal rules
from .legal.legal_hours import LegalHours

# Oncall rules
from .oncall import (
    OncallFromMainStaff,
    OncallNoConflictWithMain,
    OncallNoOffRequest,
)

# Crisis rules
from .crisis import (
    CrisisFromMainStaff,
    CrisisNoConflictWithMain,
    CrisisNoOffRequest,
)


__all__ = [
    'Rule',
    'ScheduleContext',
    'StaffInfo',
    'Violation',
    'RuleResult',
    'AggregateResult',
    'Severity',
    'RuleCategory',
    'RuleRegistry',
    'get_rule_registry',
    'MaxConsecutiveNights',
    'NoWorkAfterNight',
    'MinimumStaffCoverage',
    'MainScheduleRequired',
    'PreferredShiftForStaff',
    'FairShiftDistribution',
    'LegalHours',
    'OncallFromMainStaff',
    'OncallNoConflictWithMain',
    'OncallNoOffRequest',
    'CrisisFromMainStaff',
    'CrisisNoConflictWithMain',
    'CrisisNoOffRequest',
]