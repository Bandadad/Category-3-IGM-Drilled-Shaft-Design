"""Capacity calculations for the Mayne-Harris Type 3 IGM method."""

from __future__ import annotations

import math

from .models import CalculationInput, CalculationResult
from .validation import validate_inputs

GAMMA_WATER = 9.81  # kN/m^3
DEFAULT_ESM_TO_ESL = 0.5
DEFAULT_EB_TO_ESL = 0.4
DEFAULT_EC = 25_000_000.0  # kPa, draft composite concrete modulus
MIN_SIGMA = 1e-6


def calculate_capacity(inputs: CalculationInput) -> CalculationResult:
    """Compute shaft, base, and total capacity along with settlement parameters."""

    warnings = validate_inputs(inputs)
    assumptions = [
        "Side resistance is modeled as drained shaft friction using a representative mid-depth effective stress.",
        "For slurry construction, side resistance uses an interface angle of 0.75 phi' when computing fmax.",
        "Base resistance is modeled from the FHWA/Mayne-Harris undrained-strength correlation at the shaft tip.",
        "Below-groundwater effective stress uses gamma_sub = gamma - 9.81 kN/m^3 when direct effective stresses are not provided.",
    ]

    z_tip = inputs.z_top_socket + inputs.socket_length
    z_mid = inputs.z_top_socket + 0.5 * inputs.socket_length

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

    sigma_p_mid = estimate_preconsolidation_pressure(inputs.n60, inputs.atmospheric_pressure)
    sigma_p_tip = estimate_preconsolidation_pressure(inputs.n60, inputs.atmospheric_pressure)
    ocr_mid = sigma_p_mid / sigma_mid
    ocr_tip = sigma_p_tip / sigma_tip

    phi_deg = inputs.phi_prime_override_deg or estimate_friction_angle_deg(
        n60=inputs.n60,
        sigma_vo_eff=sigma_mid,
        atmospheric_pressure=inputs.atmospheric_pressure,
    )
    phi_rad = math.radians(phi_deg)

    k0 = inputs.k0_override or compute_k0(phi_rad=phi_rad, ocr=ocr_mid)
    interface_phi_rad = 0.75 * phi_rad if inputs.slurry_construction else phi_rad
    fmax = k0 * math.tan(interface_phi_rad) * sigma_mid
    qs_max = fmax * math.pi * inputs.diameter * inputs.socket_length
    qs = qs_max

    su = inputs.su_override or (0.23 * sigma_tip * (ocr_tip**0.8))
    qmax = 9.33 * su
    qb = qmax * base_area(inputs.diameter)
    qtotal = qs + qb
    q_design = 0.45 * qs + 0.4 * qb

    esl = inputs.esl_override or (22.0 * inputs.atmospheric_pressure * (inputs.n60**0.82))
    esm = inputs.esm_override or (DEFAULT_ESM_TO_ESL * esl)
    eb = inputs.eb_override or (DEFAULT_EB_TO_ESL * esl)
    ec = inputs.ec_override or DEFAULT_EC

    settlement = compute_settlement_parameters(
        diameter=inputs.diameter,
        socket_length=inputs.socket_length,
        nu=inputs.nu,
        esl=esl,
        esm=esm,
        eb=eb,
        ec=ec,
        qs_max=qs,
        qb_max=qb,
        branch3_extension_mm=inputs.branch3_extension_mm,
    )

    return CalculationResult(
        z_tip=z_tip,
        z_mid=z_mid,
        sigma_vo_eff_mid=sigma_mid,
        sigma_vo_eff_tip=sigma_tip,
        sigma_p_eff_mid=sigma_p_mid,
        sigma_p_eff_tip=sigma_p_tip,
        ocr_mid=ocr_mid,
        ocr_tip=ocr_tip,
        phi_prime_deg=phi_deg,
        k0=k0,
        fmax=fmax,
        qs_max=qs_max,
        qs=qs,
        su=su,
        qmax=qmax,
        qb=qb,
        qtotal=qtotal,
        q_design=q_design,
        esl=esl,
        esm=esm,
        eb=eb,
        ec=ec,
        xi=settlement["xi"],
        lambda_value=settlement["lambda_value"],
        xi_lambda=settlement["xi_lambda"],
        mu_l=settlement["mu_l"],
        influence_factor=settlement["influence_factor"],
        qt1=settlement["qt1"],
        wt1_m=settlement["wt1_m"],
        qb1=settlement["qb1"],
        wt2_m=settlement["wt2_m"],
        wt3_end_m=settlement["wt3_end_m"],
        branch2_delta_wb_m=settlement["branch2_delta_wb_m"],
        assumptions=assumptions,
        warnings=warnings,
    )


def compute_effective_stress(depth: float, groundwater_depth: float, gamma: float) -> float:
    """Compute effective stress using a single unit weight and groundwater depth."""

    if depth <= groundwater_depth:
        return gamma * depth

    gamma_sub = max(gamma - GAMMA_WATER, 1.0)
    return gamma * groundwater_depth + gamma_sub * (depth - groundwater_depth)


def estimate_preconsolidation_pressure(n60: float, atmospheric_pressure: float) -> float:
    """Estimate preconsolidation pressure from the FHWA summary correlation."""

    return 0.2 * n60 * atmospheric_pressure


def estimate_friction_angle_deg(n60: float, sigma_vo_eff: float, atmospheric_pressure: float) -> float:
    """Estimate friction angle in degrees from the confirmed FHWA summary equation."""

    ratio = n60 / (12.2 + 20.3 * (sigma_vo_eff / atmospheric_pressure))
    phi_rad = math.atan(ratio**0.34)
    return math.degrees(phi_rad)


def compute_k0(phi_rad: float, ocr: float) -> float:
    """Compute the at-rest lateral earth pressure coefficient."""

    return (1.0 - math.sin(phi_rad)) * (ocr**math.sin(phi_rad))


def base_area(diameter: float) -> float:
    """Return the shaft base area in square meters."""

    return math.pi * diameter * diameter / 4.0


def compute_settlement_parameters(
    *,
    diameter: float,
    socket_length: float,
    nu: float,
    esl: float,
    esm: float,
    eb: float,
    ec: float,
    qs_max: float,
    qb_max: float,
    branch3_extension_mm: float,
) -> dict[str, float]:
    """Compute draft settlement parameters used by the three-branch plot."""

    xi = esl / eb
    esm_ratio = esm / esl
    lambda_value = 2.0 * (1.0 + nu) * ec / esl

    # Draft transcription of the FHWA/Mayne-Harris closed-form parameter.
    ln_xi_lambda = (
        0.25 + ((2.5 * esm_ratio * (1.0 - nu) - 0.25) / xi)
    ) * (2.0 * socket_length / diameter)
    xi_lambda = math.exp(ln_xi_lambda)
    mu_l = 2.0 * math.sqrt(2.0 / xi_lambda) * (socket_length / diameter)
    tanh_mu_l = math.tanh(mu_l)
    cosh_mu_l = math.cosh(mu_l)
    mu_l_safe = max(mu_l, 1e-6)

    numerator = 4.0 * (1.0 + nu) * (
        1.0
        + (
            8.0
            * tanh_mu_l
            * socket_length
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
            * socket_length
            / (xi * mu_l_safe * diameter)
        )
    )
    influence_factor = numerator / denominator

    qt1_denominator = 1.0 - 1.0 / (xi * cosh_mu_l * (1.0 - nu) * (1.0 + nu))
    raw_qt1 = qs_max / max(qt1_denominator, 1e-6)

    # In the draft transcription, the closed-form expression can overshoot Qt,max.
    # Clamp the transition so Segment 2 remains physically meaningful until the
    # retained source equation is verified against the FHWA reference.
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
        "xi_lambda": xi_lambda,
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
    """Segment 2 settlement increment from the retained Mayne-Harris relation.

    Delta_wb = (Qt,max - Qt1) * (1 - nu) * (1 + nu) / (Eb * D)

    Units remain consistent because kPa = kN/m^2.
    """

    delta_q = max(qt_max - qt1, 0.0)
    return delta_q * (1.0 - nu) * (1.0 + nu) / (eb * diameter)
