"""Capacity and settlement calculations for the cohesionless-soil beta method."""

from __future__ import annotations

import math

from .beta_models import BetaCalculationInput, BetaCalculationResult, BetaLayerResult, BetaSoilLayer
from .beta_validation import validate_beta_inputs

GAMMA_WATER = 9.81  # kN/m^3
DEFAULT_ESM_TO_ESL = 0.5
DEFAULT_EB_TO_ESL = 0.4
DEFAULT_EC = 25_000_000.0  # kPa
MIN_SIGMA = 1e-6
QMAX_CAP_KPA = 2873.0
SHAFT_RESISTANCE_FACTOR = 0.55
BASE_RESISTANCE_FACTOR = 0.50


def calculate_beta_capacity(inputs: BetaCalculationInput) -> BetaCalculationResult:
    """Compute beta-method shaft, base, and total capacities."""

    warnings = validate_beta_inputs(inputs)
    assumptions = [
        "Side resistance is computed independently for each layer portion intersecting the shaft.",
        "Layer beta-method values use effective vertical stress at each layer midpoint.",
        "Side resistance uses each layer's unit side resistance over only the shaft length intersecting that layer.",
        "Base resistance follows qmax = 57.5 N60 capped at 2873 kPa and uses only the layer containing the shaft tip.",
        "For non-gravelly soils, the preconsolidation-pressure correlation is implemented as sigma'p = 0.47 N60^m pa to preserve units.",
        "Segment 1 through Segment 3 settlement terms retain the project's FHWA/Mayne-Harris transcription used elsewhere in this repository.",
    ]

    z_tip = inputs.z_top_shaft + inputs.shaft_length
    z_mid = inputs.z_top_shaft + 0.5 * inputs.shaft_length
    layer_depths = build_layer_depths(inputs.layers)

    layer_results: list[BetaLayerResult] = []
    for index, z_layer_top, z_layer_bottom, layer in layer_depths:
        overlap_top, overlap_bottom, overlap_length = compute_layer_overlap(
            z_layer_top=z_layer_top,
            z_layer_bottom=z_layer_bottom,
            z_shaft_top=inputs.z_top_shaft,
            z_tip=z_tip,
        )

        layer_mid = 0.5 * (z_layer_top + z_layer_bottom)
        sigma_segment = (
            inputs.sigma_vo_eff_mid_override
            if inputs.sigma_vo_eff_mid_override is not None
            else compute_layered_effective_stress(
                depth=layer_mid,
                groundwater_depth=inputs.z_gwt,
                layers=inputs.layers,
            )
        )
        sigma_segment = max(sigma_segment, MIN_SIGMA)

        sigma_p_segment = estimate_preconsolidation_pressure(
            n60=layer.n60,
            atmospheric_pressure=inputs.atmospheric_pressure,
            soil_type=inputs.soil_type,
            exponent=inputs.preconsolidation_exponent,
        )
        ocr_segment = sigma_p_segment / sigma_segment
        phi_deg = (
            inputs.phi_prime_override_deg
            if inputs.phi_prime_override_deg is not None
            else estimate_friction_angle_deg(
                n60=layer.n60,
                sigma_vo_eff=sigma_segment,
                atmospheric_pressure=inputs.atmospheric_pressure,
            )
        )
        phi_rad = math.radians(phi_deg)

        k0 = inputs.k0_override if inputs.k0_override is not None else compute_k0(phi_rad=phi_rad, ocr=ocr_segment)
        kp = compute_kp(phi_rad)
        k0 = min(k0, kp)

        n1_60_mid = layer.n60 * math.sqrt(inputs.atmospheric_pressure / sigma_segment)
        delta_rad = 0.75 * phi_rad if inputs.slurry_construction else phi_rad
        beta = k0 * math.tan(delta_rad)
        fmax = beta * sigma_segment
        qs_layer = fmax * math.pi * inputs.diameter * overlap_length

        layer_results.append(
            BetaLayerResult(
                index=index,
                z_top=z_layer_top,
                z_bottom=z_layer_bottom,
                z_mid=layer_mid,
                shaft_overlap_top=overlap_top,
                shaft_overlap_bottom=overlap_bottom,
                shaft_overlap_length=overlap_length,
                gamma=layer.gamma,
                n60=layer.n60,
                sigma_vo_eff_mid=sigma_segment,
                sigma_p_eff_mid=sigma_p_segment,
                ocr_mid=ocr_segment,
                n1_60_mid=n1_60_mid,
                phi_prime_deg=phi_deg,
                k0=k0,
                kp=kp,
                beta=beta,
                fmax=fmax,
                qs=qs_layer,
            )
        )

    tip_layer_index, _, _, tip_layer = find_layer_at_depth(layer_depths, z_tip)
    sigma_tip = (
        inputs.sigma_vo_eff_tip_override
        if inputs.sigma_vo_eff_tip_override is not None
        else compute_layered_effective_stress(
            depth=z_tip,
            groundwater_depth=inputs.z_gwt,
            layers=inputs.layers,
        )
    )
    sigma_tip = max(sigma_tip, MIN_SIGMA)

    sigma_p_tip = estimate_preconsolidation_pressure(
        n60=tip_layer.n60,
        atmospheric_pressure=inputs.atmospheric_pressure,
        soil_type=inputs.soil_type,
        exponent=inputs.preconsolidation_exponent,
    )
    ocr_tip = sigma_p_tip / sigma_tip

    qs = sum(layer_result.qs for layer_result in layer_results)
    side_layer_results = [item for item in layer_results if item.shaft_overlap_length > 0.0]
    weighted_n60 = _weighted_average((item.n60, item.shaft_overlap_length) for item in side_layer_results)
    sigma_mid = _weighted_average((item.sigma_vo_eff_mid, item.shaft_overlap_length) for item in side_layer_results)
    sigma_p_mid = _weighted_average((item.sigma_p_eff_mid, item.shaft_overlap_length) for item in side_layer_results)
    ocr_mid = _weighted_average((item.ocr_mid, item.shaft_overlap_length) for item in side_layer_results)
    n1_60_mid = _weighted_average((item.n1_60_mid, item.shaft_overlap_length) for item in side_layer_results)
    phi_deg = _weighted_average((item.phi_prime_deg, item.shaft_overlap_length) for item in side_layer_results)
    k0 = max((item.k0 for item in side_layer_results), default=0.0)
    kp = max((item.kp for item in side_layer_results), default=0.0)
    fmax = max((item.fmax for item in side_layer_results), default=0.0)

    qmax = min(57.5 * tip_layer.n60, QMAX_CAP_KPA)
    qb = qmax * base_area(inputs.diameter)
    q_design = (SHAFT_RESISTANCE_FACTOR * qs) + (BASE_RESISTANCE_FACTOR * qb)
    qtotal = qs + qb

    esl = inputs.esl_override or (22.0 * inputs.atmospheric_pressure * (weighted_n60**0.82))
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
        layer_results=layer_results,
        tip_layer_index=tip_layer_index,
        tip_layer_gamma=tip_layer.gamma,
        tip_layer_n60=tip_layer.n60,
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
        q_design=q_design,
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


def build_layer_depths(layers: list[BetaSoilLayer]) -> list[tuple[int, float, float, BetaSoilLayer]]:
    """Return layer depth intervals measured from grade."""

    layer_depths: list[tuple[int, float, float, BetaSoilLayer]] = []
    current_top = 0.0
    for index, layer in enumerate(layers, start=1):
        current_bottom = current_top + layer.thickness
        layer_depths.append((index, current_top, current_bottom, layer))
        current_top = current_bottom
    return layer_depths


def find_layer_at_depth(
    layer_depths: list[tuple[int, float, float, BetaSoilLayer]],
    depth: float,
) -> tuple[int, float, float, BetaSoilLayer]:
    """Return the layer containing depth, using the lower layer at internal boundaries."""

    for index, z_top, z_bottom, layer in layer_depths:
        if z_top <= depth < z_bottom:
            return index, z_top, z_bottom, layer

    if layer_depths and math.isclose(depth, layer_depths[-1][2]):
        return layer_depths[-1]

    raise ValueError("Layer profile does not extend to the requested depth.")


def compute_layer_overlap(
    *,
    z_layer_top: float,
    z_layer_bottom: float,
    z_shaft_top: float,
    z_tip: float,
) -> tuple[float, float, float]:
    """Return the portion of a layer intersecting the shaft."""

    overlap_top = max(z_layer_top, z_shaft_top)
    overlap_bottom = min(z_layer_bottom, z_tip)
    overlap_length = max(overlap_bottom - overlap_top, 0.0)
    return overlap_top, overlap_bottom, overlap_length


def compute_layered_effective_stress(
    *,
    depth: float,
    groundwater_depth: float,
    layers: list[BetaSoilLayer],
) -> float:
    """Compute vertical effective stress by integrating a layered profile."""

    if depth <= 0.0:
        return 0.0

    stress = 0.0
    for _, z_top, z_bottom, layer in build_layer_depths(layers):
        if z_top >= depth:
            break

        interval_top = z_top
        interval_bottom = min(z_bottom, depth)
        if interval_bottom <= interval_top:
            continue

        if interval_bottom <= groundwater_depth:
            stress += layer.gamma * (interval_bottom - interval_top)
            continue

        gamma_sub = max(layer.gamma - GAMMA_WATER, 1.0)
        if interval_top >= groundwater_depth:
            stress += gamma_sub * (interval_bottom - interval_top)
            continue

        stress += layer.gamma * (groundwater_depth - interval_top)
        stress += gamma_sub * (interval_bottom - groundwater_depth)

    return stress


def _weighted_average(values_and_weights) -> float:
    """Return a length-weighted average for aggregate display fields."""

    total_weight = 0.0
    weighted_sum = 0.0
    for value, weight in values_and_weights:
        total_weight += weight
        weighted_sum += value * weight
    if total_weight <= 0.0:
        return 0.0
    return weighted_sum / total_weight


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
