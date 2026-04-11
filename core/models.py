"""Dataclasses shared by the GUI, engineering core, and tests."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CalculationInput:
    """User inputs for the Mayne-Harris draft calculation."""

    gamma: float = 20.0
    slurry_construction: bool = False
    z_gwt: float = 2.0
    z_top_socket: float = 6.0
    socket_length: float = 8.0
    diameter: float = 1.2
    n60: float = 65.0
    nu: float = 0.30
    sigma_vo_eff_mid_override: float | None = None
    sigma_vo_eff_tip_override: float | None = None
    phi_prime_override_deg: float | None = None
    k0_override: float | None = None
    esl_override: float | None = None
    esm_override: float | None = None
    eb_override: float | None = None
    ec_override: float | None = None
    su_override: float | None = None
    atmospheric_pressure: float = 101.0
    branch3_extension_mm: float = 10.0
    points_per_segment: int = 30


@dataclass(slots=True)
class CalculationResult:
    """Computed capacities and intermediate quantities."""

    z_tip: float
    z_mid: float
    sigma_vo_eff_mid: float
    sigma_vo_eff_tip: float
    sigma_p_eff_mid: float
    sigma_p_eff_tip: float
    ocr_mid: float
    ocr_tip: float
    phi_prime_deg: float
    k0: float
    fmax: float
    qs_max: float
    qs: float
    su: float
    qmax: float
    qb: float
    qtotal: float
    q_design: float
    esl: float
    esm: float
    eb: float
    ec: float
    xi: float
    lambda_value: float
    xi_lambda: float
    mu_l: float
    influence_factor: float
    qt1: float
    wt1_m: float
    qb1: float
    wt2_m: float
    wt3_end_m: float
    branch2_delta_wb_m: float
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CurveResult:
    """Three-branched load-settlement response."""

    settlements_m: list[float]
    loads_kN: list[float]
    segment_breaks_m: list[float]
    segment_breaks_kN: list[float]
    labels: list[str]
