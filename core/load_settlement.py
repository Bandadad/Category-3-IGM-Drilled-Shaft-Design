"""Generation of the three-branched Mayne-Harris draft load-settlement curve."""

from __future__ import annotations

from .models import CalculationInput, CalculationResult, CurveResult


def generate_three_branch_curve(
    inputs: CalculationInput,
    result: CalculationResult,
) -> CurveResult:
    """Return discretized settlements and loads for the three-branch curve."""

    first_settlements = _linspace(0.0, result.wt1_m, inputs.points_per_segment)
    first_loads = _linspace(0.0, result.qt1, inputs.points_per_segment)

    second_settlements = _linspace(result.wt1_m, result.wt2_m, inputs.points_per_segment)
    second_loads = _linspace(result.qt1, result.qtotal, inputs.points_per_segment)

    third_settlements = _linspace(result.wt2_m, result.wt3_end_m, inputs.points_per_segment)
    third_loads = [result.qtotal for _ in range(inputs.points_per_segment)]

    settlements = first_settlements + second_settlements[1:] + third_settlements[1:]
    loads = first_loads + second_loads[1:] + third_loads[1:]

    return CurveResult(
        settlements_m=settlements,
        loads_kN=loads,
        segment_breaks_m=[0.0, result.wt1_m, result.wt2_m, result.wt3_end_m],
        segment_breaks_kN=[0.0, result.qt1, result.qtotal, result.qtotal],
        labels=["Segment 1", "Segment 2", "Segment 3"],
    )


def _linspace(start: float, end: float, count: int) -> list[float]:
    """Generate linearly spaced values without requiring numpy."""

    if count == 1:
        return [end]
    step = (end - start) / (count - 1)
    return [start + step * index for index in range(count)]
