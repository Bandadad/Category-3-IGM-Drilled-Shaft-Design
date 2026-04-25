"""Dataclasses for the cohesionless-soil beta method calculator."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class BetaSoilLayer:
    """One soil layer in the beta-method profile."""

    thickness: float = 12.0
    gamma: float = 18.0
    n60: float = 25.0


@dataclass(slots=True)
class BetaCalculationInput:
    """User inputs for the FHWA beta method in cohesionless soil."""

    layers: list[BetaSoilLayer] = field(default_factory=lambda: [BetaSoilLayer()])
    z_gwt: float = 2.0
    z_top_shaft: float = 1.5
    shaft_length: float = 10.0
    diameter: float = 1.0
    nu: float = 0.30
    slurry_construction: bool = False
    soil_type: str = "other"
    preconsolidation_exponent: float = 0.8
    sigma_vo_eff_mid_override: float | None = None
    sigma_vo_eff_tip_override: float | None = None
    phi_prime_override_deg: float | None = None
    k0_override: float | None = None
    esl_override: float | None = None
    esm_override: float | None = None
    eb_override: float | None = None
    ec_override: float | None = None
    atmospheric_pressure: float = 101.0
    branch3_extension_mm: float = 10.0
    points_per_segment: int = 30


@dataclass(slots=True)
class BetaLayerResult:
    """Computed beta-method values for one soil layer."""

    index: int
    z_top: float
    z_bottom: float
    z_mid: float
    shaft_overlap_top: float
    shaft_overlap_bottom: float
    shaft_overlap_length: float
    gamma: float
    n60: float
    sigma_vo_eff_mid: float
    sigma_p_eff_mid: float
    ocr_mid: float
    n1_60_mid: float
    phi_prime_deg: float
    k0: float
    kp: float
    beta: float
    fmax: float
    qs: float


@dataclass(slots=True)
class BetaCalculationResult:
    """Computed capacities and intermediate values for the beta method."""

    layer_results: list[BetaLayerResult]
    tip_layer_index: int
    tip_layer_gamma: float
    tip_layer_n60: float
    shaft_mid_layer_index: int
    shaft_mid_layer_n60: float
    z_tip: float
    z_mid: float
    sigma_vo_eff_mid: float
    sigma_vo_eff_tip: float
    sigma_p_eff_mid: float
    sigma_p_eff_tip: float
    ocr_mid: float
    ocr_tip: float
    n1_60_mid: float
    phi_prime_deg: float
    k0: float
    kp: float
    fmax: float
    qs: float
    qmax: float
    qb: float
    q_design: float
    qtotal: float
    esl: float
    esm: float
    eb: float
    ec: float
    xi: float
    lambda_value: float
    zeta: float
    mu_l: float
    influence_factor: float
    qt1: float
    qb1: float
    wt1_m: float
    wt2_m: float
    wt3_end_m: float
    branch2_delta_wb_m: float
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BetaCurveResult:
    """Three-branched load-settlement response for the beta method."""

    settlements_m: list[float]
    loads_kN: list[float]
    segment_breaks_m: list[float]
    segment_breaks_kN: list[float]
    labels: list[str]
