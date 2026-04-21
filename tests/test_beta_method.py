"""Unit tests for the cohesionless-soil beta method calculator."""

from __future__ import annotations

import math
import unittest

from core.beta_calculations import base_area, calculate_beta_capacity
from core.beta_load_settlement import generate_beta_three_branch_curve
from core.beta_models import BetaCalculationInput
from core.beta_validation import BetaValidationError


class BetaMethodEngineeringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = BetaCalculationInput()

    def test_base_area(self) -> None:
        self.assertAlmostEqual(base_area(1.0), math.pi / 4.0)

    def test_capacity_components_sum(self) -> None:
        result = calculate_beta_capacity(self.inputs)
        self.assertGreater(result.qs, 0.0)
        self.assertGreater(result.qb, 0.0)
        self.assertAlmostEqual(result.qtotal, result.qs + result.qb)

    def test_qmax_is_capped(self) -> None:
        result = calculate_beta_capacity(BetaCalculationInput(n60=100.0))
        self.assertAlmostEqual(result.qmax, 2873.0)

    def test_invalid_inputs_raise(self) -> None:
        with self.assertRaises(BetaValidationError):
            calculate_beta_capacity(BetaCalculationInput(diameter=0.0))

    def test_curve_has_three_ordered_branches(self) -> None:
        result = calculate_beta_capacity(self.inputs)
        curve = generate_beta_three_branch_curve(self.inputs, result)

        self.assertEqual(len(curve.labels), 3)
        self.assertLess(curve.segment_breaks_m[1], curve.segment_breaks_m[2])
        self.assertLess(curve.segment_breaks_m[2], curve.segment_breaks_m[3])
        self.assertAlmostEqual(curve.segment_breaks_kN[2], curve.segment_breaks_kN[3])

    def test_settlement_values_are_monotonic(self) -> None:
        result = calculate_beta_capacity(self.inputs)
        curve = generate_beta_three_branch_curve(self.inputs, result)

        for first, second in zip(curve.settlements_m, curve.settlements_m[1:]):
            self.assertLessEqual(first, second)

    def test_k0_is_bounded_by_kp(self) -> None:
        result = calculate_beta_capacity(BetaCalculationInput(n60=80.0))
        self.assertLessEqual(result.k0, result.kp)

    def test_gravelly_and_other_soils_use_different_sigma_p(self) -> None:
        gravelly = calculate_beta_capacity(BetaCalculationInput(soil_type="gravelly"))
        other = calculate_beta_capacity(BetaCalculationInput(soil_type="other"))
        self.assertNotAlmostEqual(gravelly.sigma_p_eff_mid, other.sigma_p_eff_mid)


if __name__ == "__main__":
    unittest.main()
