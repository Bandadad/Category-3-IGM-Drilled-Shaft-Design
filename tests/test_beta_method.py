"""Unit tests for the cohesionless-soil beta method calculator."""

from __future__ import annotations

import math
import unittest

from core.beta_calculations import (
    base_area,
    calculate_beta_capacity,
    compute_layer_overlap,
    compute_layered_effective_stress,
    estimate_soil_modulus_from_n60,
)
from core.beta_load_settlement import generate_beta_three_branch_curve
from core.beta_models import BetaCalculationInput, BetaSoilLayer
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

    def test_design_capacity_uses_factored_components(self) -> None:
        result = calculate_beta_capacity(self.inputs)
        self.assertAlmostEqual(result.q_design, (0.55 * result.qs) + (0.50 * result.qb))

    def test_qmax_is_capped(self) -> None:
        result = calculate_beta_capacity(BetaCalculationInput(layers=[BetaSoilLayer(thickness=12.0, gamma=18.0, n60=100.0)]))
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
        result = calculate_beta_capacity(BetaCalculationInput(layers=[BetaSoilLayer(thickness=12.0, gamma=18.0, n60=80.0)]))
        self.assertLessEqual(result.k0, result.kp)

    def test_gravelly_and_other_soils_use_different_sigma_p(self) -> None:
        gravelly = calculate_beta_capacity(BetaCalculationInput(soil_type="gravelly"))
        other = calculate_beta_capacity(BetaCalculationInput(soil_type="other"))
        self.assertNotAlmostEqual(gravelly.sigma_p_eff_mid, other.sigma_p_eff_mid)

    def test_layered_effective_stress_above_groundwater(self) -> None:
        layers = [
            BetaSoilLayer(thickness=2.0, gamma=18.0, n60=20.0),
            BetaSoilLayer(thickness=3.0, gamma=20.0, n60=30.0),
        ]

        stress = compute_layered_effective_stress(depth=4.0, groundwater_depth=10.0, layers=layers)

        self.assertAlmostEqual(stress, (2.0 * 18.0) + (2.0 * 20.0))

    def test_layered_effective_stress_splits_at_groundwater(self) -> None:
        layers = [BetaSoilLayer(thickness=5.0, gamma=19.81, n60=20.0)]

        stress = compute_layered_effective_stress(depth=4.0, groundwater_depth=2.0, layers=layers)

        self.assertAlmostEqual(stress, (2.0 * 19.81) + (2.0 * 10.0))

    def test_layer_overlap_handles_partial_layers(self) -> None:
        overlap_top, overlap_bottom, overlap_length = compute_layer_overlap(
            z_layer_top=0.0,
            z_layer_bottom=3.0,
            z_shaft_top=1.0,
            z_tip=5.0,
        )

        self.assertAlmostEqual(overlap_top, 1.0)
        self.assertAlmostEqual(overlap_bottom, 3.0)
        self.assertAlmostEqual(overlap_length, 2.0)

    def test_multilayer_capacity_sums_side_resistance_and_uses_tip_layer_for_base(self) -> None:
        inputs = BetaCalculationInput(
            layers=[
                BetaSoilLayer(thickness=3.0, gamma=18.0, n60=20.0),
                BetaSoilLayer(thickness=4.0, gamma=20.0, n60=40.0),
            ],
            z_top_shaft=1.0,
            shaft_length=4.0,
            diameter=1.0,
            z_gwt=10.0,
        )

        result = calculate_beta_capacity(inputs)

        self.assertEqual(len(result.layer_results), 2)
        self.assertAlmostEqual(result.layer_results[0].shaft_overlap_length, 2.0)
        self.assertAlmostEqual(result.layer_results[1].shaft_overlap_length, 2.0)
        self.assertAlmostEqual(result.qs, sum(layer.qs for layer in result.layer_results))
        self.assertEqual(result.tip_layer_index, 2)
        self.assertAlmostEqual(result.qmax, 57.5 * 40.0)

    def test_settlement_moduli_use_tip_and_shaft_midpoint_layers(self) -> None:
        inputs = BetaCalculationInput(
            layers=[
                BetaSoilLayer(thickness=3.0, gamma=18.0, n60=10.0),
                BetaSoilLayer(thickness=4.0, gamma=20.0, n60=30.0),
                BetaSoilLayer(thickness=5.0, gamma=21.0, n60=60.0),
            ],
            z_top_shaft=1.0,
            shaft_length=8.0,
            diameter=1.0,
            z_gwt=20.0,
        )

        result = calculate_beta_capacity(inputs)

        self.assertEqual(result.shaft_mid_layer_index, 2)
        self.assertEqual(result.tip_layer_index, 3)
        self.assertAlmostEqual(
            result.esl,
            estimate_soil_modulus_from_n60(n60=60.0, atmospheric_pressure=inputs.atmospheric_pressure),
        )
        self.assertAlmostEqual(
            result.esm,
            estimate_soil_modulus_from_n60(n60=30.0, atmospheric_pressure=inputs.atmospheric_pressure),
        )
        self.assertAlmostEqual(result.eb, 0.4 * result.esl)

    def test_layer_results_use_layer_mid_depth_and_report_beta(self) -> None:
        inputs = BetaCalculationInput(
            layers=[
                BetaSoilLayer(thickness=3.0, gamma=18.0, n60=20.0),
                BetaSoilLayer(thickness=4.0, gamma=20.0, n60=40.0),
            ],
            z_top_shaft=1.0,
            shaft_length=4.0,
            diameter=1.0,
            z_gwt=10.0,
        )

        result = calculate_beta_capacity(inputs)
        first_layer = result.layer_results[0]
        second_layer = result.layer_results[1]

        self.assertAlmostEqual(first_layer.z_mid, 2.0)
        self.assertAlmostEqual(second_layer.z_mid, 4.0)
        self.assertAlmostEqual(first_layer.sigma_vo_eff_mid, 18.0 * 2.0)
        self.assertAlmostEqual(second_layer.sigma_vo_eff_mid, (18.0 * 3.0) + (20.0 * 1.0))
        self.assertAlmostEqual(first_layer.fmax, first_layer.beta * first_layer.sigma_vo_eff_mid)
        self.assertGreater(first_layer.beta, 0.0)

    def test_rejects_more_than_six_layers(self) -> None:
        with self.assertRaises(BetaValidationError):
            calculate_beta_capacity(BetaCalculationInput(layers=[BetaSoilLayer() for _ in range(7)]))

    def test_rejects_profile_that_does_not_reach_tip(self) -> None:
        with self.assertRaises(BetaValidationError):
            calculate_beta_capacity(
                BetaCalculationInput(
                    layers=[BetaSoilLayer(thickness=2.0, gamma=18.0, n60=20.0)],
                    z_top_shaft=1.0,
                    shaft_length=4.0,
                )
            )


if __name__ == "__main__":
    unittest.main()
