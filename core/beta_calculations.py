"""Capacity and settlement calculations for the cohesionless-soil beta method."""

from __future__ import annotations

import math

from .beta_models import BetaCalculationInput, BetaCalculationResult
from .beta_validation import validate_beta_inputs

GAMMA_WATER = 9.81  # kN/m^3
DEFAULT_ESM_TO_ESL = 0.5
DEFAULT_EB_TO_ESL = 0.4
DEFAULT_EC = 25_000_000.0  # kPa
MIN_SIGMA = 1e-6
QMAX_CAP_KPA = 2873.0


def calculate_beta_capacity(inputs: BetaCalculationInput) -> BetaCalculationResult:
    """Compute beta-method shaft, base, and total capacities."""

    warnings = validate_beta_inputs(inputs)
    assumptions = [
        "The cohesionless-soil beta method uses representative mid-depth effective stress for side resistance.",
        "Base resistance follows the explicit SPT correlation qmax = 57.5 N60 capped at 2873 kPa from beta_method.md.",
        "For non-gravelly soils, the preconsolidation-pressure correlation is implemented as sigma'p = 0.47 N60^m pa to preserve units.",
        "Segment 1 through Segment 3 settlement terms retain the project's FHWA/Mayne-Harris transcription used elsewhere in this repository.",
    ]

    z_tip = inputs.z_top_shaft + inputs.shaft_length
    z_mid = inputs.z_top_shaft + 0.5 * inputs.shaft_length

    sigma_mid = inputs.sigma_vo_eff_mid_override or compute_effective_stress(
        depth=z_mid,
        groundwater_depth=inputs.z_gwt,
        gamma=inputs.gamma,
    )
    sigma_tip = inputs.sigma_vo_eff_tip_override or compute_effective_stress(
        depth=z_tip,
        groundwater_depth=inputs.z_gwt,
        gamma=inputs.gamma,
    )
    sigma_mid = max(sigma_mid, MIN_SIGMA)
    sigma_tip = max(sigma_tip, MIN_SIGMA)

    sigma_p_mid = estimate_preconsolidation_pressure(
        n60=inputs.n60,
        atmospheric_pressure=inputs.atmospheric_pressure,
        soil_type=inputs.soil_type,
        exponent=inputs.preconsolidation_exponent,
    )
    sigma_p_tip = sigma_p_mid
    ocr_mid = sigma_p_mid / sigma_mid
    ocr_tip = sigma_p_tip / sigma_tip

    phi_deg = inputs.phi_prime_override_deg or estimate_friction_angle_deg(
        n60=inputs.n60,
        sigma_vo_eff=sigma_mid,
        atmospheric_pressure=inputs.atmospheric_pressure,
    )
    phi_rad = math.radians(phi_deg)

    k0 = inputs.k0_override or compute_k0(phi_rad=phi_rad, ocr=ocr_mid)
    kp = compute_kp(phi_rad)
    k0 = min(k0, kp)

    n1_60_mid = inputs.n60 * math.sqrt(inputs.atmospheric_pressure / sigma_mid)
    delta_rad = 0.75 * phi_rad if inputs.slurry_construction else phi_rad
    fmax = k0 * math.tan(delta_rad) * sigma_mid
    qs = fmax * math.pi * inputs.diameter * inputs.shaft_length

    qmax = min(57.5 * inputs.n60, QMAX_CAP_KPA)
    qb = qmax * base_area(inputs.diameter)
    qtotal = qs + qb

    esl = inputs.esl_override or (22.0 * inputs.atmospheric_pressure * (inputs.n60**0.82))
    esm = inputs.esm_override or (DEFAULT_ESM_TO_ESL * esl)
    eb = inputs.eb_override or (DEFAULT_EB_TO_ESL * esl)
    ec = inputs.ec_override or DEFAULT_EC

    settlement = compute_settlement_parameters(
        diameter=inputs.diameter,
        shaft_length=inputs.shaft_length,
        nu=inputs.nu,
        esl=esl,
        esm=esm,
        eb=eb,
        ec=ec,
        qs_max=qs,
        qb_max=qb,
        branch3_extension_mm=inputs.branch3_extension_mm,
    )

    return BetaCalculationResult(
        z_tip=z_tip,
        z_mid=z_mid,
        sigma_vo_eff_mid=sigma_mid,
        sigma_vo_eff_tip=sigma_tip,
        sigma_p_eff_mid=sigma_p_mid,
        sigma_p_eff_tip=sigma_p_tip,
        ocr_mid=ocr_mid,
        ocr_tip=ocr_tip,
        n1_60_mid=n1_60_mid,
        phi_prime_deg=phi_deg,
        k0=k0,
        kp=kp,
        fmax=fmax,
        qs=qs,
        qmax=qmax,
        qb=qb,
        qtotal=qtotal,
        esl=esl,
        esm=esm,
        eb=eb,
        ec=ec,
        xi=settlement["xi"],
        lambda_value=settlement["lambda_value"],
        zeta=settlement["zeta"],
        mu_l=settlement["mu_l"],
        influence_factor=settlement["influence_factor"],
        qt1=settlement["qt1"],
        qb1=settlement["qb1"],
        wt1_m=settlement["wt1_m"],
        wt2_m=settlement["wt2_m"],
        wt3_end_m=settlement["wt3_end_m"],
        branch2_delta_wb_m=settlement["branch2_delta_wb_m"],
        assumptions=assumptions,
        warnings=warnings,
    )


def compute_effective_stress(depth: float, groundwater_depth: float, gamma: float) -> float:
    """Compute effective stress using one representative unit weight."""

    if depth <= groundwater_depth:
        return gamma * depth

    gamma_sub = max(gamma - GAMMA_WATER, 1.0)
    return gamma * groundwater_depth + gamma_sub * (depth - groundwater_depth)


def estimate_preconsolidation_pressure(
    *,
    n60: float,
    atmospheric_pressure: float,
    soil_type: str,
    exponent: float,
) -> float:
    """Estimate effective preconsolidation pressure in kPa."""

    if soil_type == "gravelly":
        return 0.15 * n60 * atmospheric_pressure

    return 0.47 * (n60**exponent) * atmospheric_pressure


def estimate_friction_angle_deg(n60: float, sigma_vo_eff: float, atmospheric_pressure: float) -> float:
    """Estimate phi' using the overburden-corrected SPT relation."""

    n1_60 = max(n60 * math.sqrt(atmospheric_pressure / max(sigma_vo_eff, MIN_SIGMA)), 1e-6)
    return 27.5 + 9.2 * math.log10(n1_60)


def compute_k0(*, phi_rad: float, ocr: float) -> float:
    """Compute K0 with the FHWA OCR correction."""

    return (1.0 - math.sin(phi_rad)) * (ocr**math.sin(phi_rad))


def compute_kp(phi_rad: float) -> float:
    """Compute the passive earth pressure coefficient."""

    return math.tan((math.pi / 4.0) + (phi_rad / 2.0)) ** 2


def base_area(diameter: float) -> float:
    """Return shaft base area in square meters."""

    return math.pi * diameter * diameter / 4.0


def compute_settlement_parameters(
    *,
    diameter: float,
    shaft_length: float,
    nu: float,
    esl: float,
    esm: float,
    eb: float,
    ec: float,
    qs_max: float,
    qb_max: float,
    branch3_extension_mm: float,
) -> dict[str, float]:
    """Compute the retained three-branch settlement parameters."""

    xi = esl / eb
    esm_ratio = esm / esl
    lambda_value = 2.0 * (1.0 + nu) * ec / esl

    zeta = math.log(
        (0.25 + (2.5 * esm_ratio * (1.0 - nu) - 0.25) * xi)
        * (2.0 * shaft_length / diameter)
    )
    mu_l = 2.0 * math.sqrt(2.0 / (zeta * lambda_value)) * (shaft_length / diameter)
    tanh_mu_l = math.tanh(mu_l)
    cosh_mu_l = math.cosh(mu_l)
    mu_l_safe = max(mu_l, 1e-6)

    numerator = 4.0 * (1.0 + nu) * (
        1.0
        + (
            8.0
            * tanh_mu_l
            * shaft_length
            / (math.pi * lambda_value * (1.0 - nu) * xi * mu_l_safe * diameter)
        )
    )
    denominator = (
        4.0 / ((1.0 - nu) * xi)
        + (
            4.0
            * math.pi
            * esm_ratio
            * tanh_mu_l
            * shaft_length
            / (zeta * mu_l_safe * diameter)
        )
    )
    influence_factor = numerator / denominator

    qt1_denominator = 1.0 - influence_factor / (xi * cosh_mu_l * (1.0 - nu) * (1.0 + nu))
    raw_qt1 = qs_max / max(qt1_denominator, 1e-6)

    qt1_upper_bound = qs_max + 0.75 * qb_max
    qt1 = min(raw_qt1, qt1_upper_bound)
    qt1 = min(qt1, qs_max + qb_max - 1e-6)
    qt1 = max(qt1, qs_max)
    wt1_m = (qt1 * influence_factor) / (esl * diameter)
    qb1 = max(qt1 - qs_max, 0.0)

    branch2_delta_wb_m = compute_base_settlement_increment(
        qt1=qt1,
        qt_max=qs_max + qb_max,
        eb=eb,
        diameter=diameter,
        nu=nu,
    )
    wt2_m = wt1_m + branch2_delta_wb_m
    wt3_end_m = wt2_m + max(branch3_extension_mm / 1000.0, 0.01 * diameter)

    return {
        "xi": xi,
        "lambda_value": lambda_value,
        "zeta": zeta,
        "mu_l": mu_l,
        "influence_factor": influence_factor,
        "qt1": qt1,
        "wt1_m": wt1_m,
        "qb1": qb1,
        "wt2_m": wt2_m,
        "wt3_end_m": wt3_end_m,
        "branch2_delta_wb_m": branch2_delta_wb_m,
    }


def compute_base_settlement_increment(
    *,
    qt1: float,
    qt_max: float,
    eb: float,
    diameter: float,
    nu: float,
) -> float:
    """Compute the Segment 2 base-settlement increment."""

    delta_q = max(qt_max - qt1, 0.0)
    return delta_q * (1.0 - nu) * (1.0 + nu) / (eb * diameter)
