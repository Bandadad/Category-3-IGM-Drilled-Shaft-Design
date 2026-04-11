"""Core engineering modules for the Type 3 IGM calculator."""

from .calculations import calculate_capacity
from .load_settlement import generate_three_branch_curve
from .models import CalculationInput, CalculationResult, CurveResult
from .validation import ValidationError, validate_inputs

__all__ = [
    "CalculationInput",
    "CalculationResult",
    "CurveResult",
    "ValidationError",
    "calculate_capacity",
    "generate_three_branch_curve",
    "validate_inputs",
]
