# ai_module/rules/soft/__init__.py
from .preferred_shift import PreferredShiftForStaff
from .fair_distribution import FairShiftDistribution

__all__ = [
    'PreferredShiftForStaff',
    'FairShiftDistribution',
]