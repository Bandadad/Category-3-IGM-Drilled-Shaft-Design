"""Unit tests for the Type 3 IGM Mayne-Harris draft calculator."""

from __future__ import annotations

import math
import unittest

from core.calculations import base_area, calculate_capacity
from core.load_settlement import generate_three_branch_curve
from core.models import CalculationInput
from core.validation import ValidationError


class EngineeringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = CalculationInput()

    def test_base_area(self) -> None:
        self.assertAlmostEqual(base_area(1.2), math.pi * 1.2**2 / 4.0)

    def test_capacity_components_sum(self) -> None:
        result = calculate_capacity(self.inputs)
        self.assertGreater(result.qs, 0.0)
        self.assertGreater(result.qb, 0.0)
        self.assertAlmostEqual(result.qs_max, result.fmax * math.pi * self.inputs.diameter * self.inputs.socket_length)
        self.assertAlmostEqual(result.qs, result.qs_max)
        self.assertAlmostEqual(result.qtotal, result.qs + result.qb)
        self.assertAlmostEqual(result.q_design, 0.45 * result.qs + 0.4 * result.qb)

    def test_invalid_inputs_raise(self) -> None:
        with self.assertRaises(ValidationError):
            calculate_capacity(CalculationInput(diameter=0.0))

    def test_curve_has_three_ordered_branches(self) -> None:
        result = calculate_capacity(self.inputs)
        curve = generate_three_branch_curve(self.inputs, result)

        self.assertEqual(len(curve.labels), 3)
        self.assertLess(curve.segment_breaks_m[1], curve.segment_breaks_m[2])
        self.assertLess(curve.segment_breaks_m[2], curve.segment_breaks_m[3])
        self.assertAlmostEqual(curve.segment_breaks_kN[2], curve.segment_breaks_kN[3])

    def test_settlement_values_are_monotonic(self) -> None:
        result = calculate_capacity(self.inputs)
        curve = generate_three_branch_curve(self.inputs, result)

        for first, second in zip(curve.settlements_m, curve.settlements_m[1:]):
            self.assertLessEqual(first, second)

    def test_segment_three_is_horizontal(self) -> None:
        result = calculate_capacity(self.inputs)
        curve = generate_three_branch_curve(self.inputs, result)
        third_start = curve.segment_breaks_kN[2]
        third_end = curve.segment_breaks_kN[3]
        self.assertAlmostEqual(third_start, third_end)

    def test_n60_warning_is_exposed(self) -> None:
        result = calculate_capacity(CalculationInput(n60=110.0))
        self.assertTrue(any("caution" in warning.lower() for warning in result.warnings))

    def test_slurry_construction_reduces_side_resistance(self) -> None:
        base_case = calculate_capacity(CalculationInput(slurry_construction=False))
        slurry_case = calculate_capacity(CalculationInput(slurry_construction=True))

        self.assertLess(slurry_case.fmax, base_case.fmax)
        self.assertLess(slurry_case.qs, base_case.qs)


if __name__ == "__main__":
    unittest.main()
