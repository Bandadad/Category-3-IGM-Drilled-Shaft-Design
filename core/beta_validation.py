"""Input validation for the cohesionless-soil beta method app."""

from __future__ import annotations

from dataclasses import fields

from .beta_models import BetaCalculationInput


class BetaValidationError(ValueError):
    """Raised when beta-method inputs are physically or numerically invalid."""


def validate_beta_inputs(inputs: BetaCalculationInput) -> list[str]:
    """Validate beta-method inputs and return non-fatal warning messages."""

    if not inputs.layers:
        raise BetaValidationError("At least one soil layer is required.")
    if len(inputs.layers) > 6:
        raise BetaValidationError("The beta-method layer table supports a maximum of 6 layers.")
    for index, layer in enumerate(inputs.layers, start=1):
        if layer.thickness <= 0:
            raise BetaValidationError(f"Layer {index} thickness must be positive.")
        if layer.gamma <= 0:
            raise BetaValidationError(f"Layer {index} unit weight must be positive.")
        if layer.n60 <= 0:
            raise BetaValidationError(f"Layer {index} N60 must be positive.")

    if inputs.diameter <= 0:
        raise BetaValidationError("Shaft diameter must be positive.")
    if inputs.shaft_length <= 0:
        raise BetaValidationError("Shaft length must be positive.")
    if inputs.nu < 0.0 or inputs.nu >= 0.5:
        raise BetaValidationError("Poisson's ratio must be between 0.0 and 0.5.")
    if inputs.z_top_shaft < 0:
        raise BetaValidationError("Depth to top of shaft cannot be negative.")
    if inputs.z_gwt < 0:
        raise BetaValidationError("Groundwater depth cannot be negative.")
    if inputs.atmospheric_pressure <= 0:
        raise BetaValidationError("Atmospheric pressure must be positive.")
    if inputs.preconsolidation_exponent <= 0:
        raise BetaValidationError("The preconsolidation exponent m must be positive.")
    if inputs.branch3_extension_mm <= 0:
        raise BetaValidationError("Branch 3 plot extension must be positive.")
    if inputs.points_per_segment < 2:
        raise BetaValidationError("Plot discretization must be at least 2 points per segment.")
    if inputs.soil_type not in {"gravelly", "other"}:
        raise BetaValidationError("Soil type must be either 'gravelly' or 'other'.")
    if sum(layer.thickness for layer in inputs.layers) < inputs.z_top_shaft + inputs.shaft_length:
        raise BetaValidationError("Layer thicknesses must extend to or below the shaft tip.")

    optional_positive_fields = {
        "sigma_vo_eff_mid_override": "Direct mid-depth effective stress",
        "sigma_vo_eff_tip_override": "Direct tip effective stress",
        "k0_override": "Direct K0",
        "esl_override": "EsL override",
        "esm_override": "Esm override",
        "eb_override": "Eb override",
        "ec_override": "Ec override",
    }
    for field in fields(inputs):
        value = getattr(inputs, field.name)
        if field.name in optional_positive_fields and value is not None and value <= 0:
            raise BetaValidationError(f"{optional_positive_fields[field.name]} must be positive.")

    if inputs.phi_prime_override_deg is not None:
        if inputs.phi_prime_override_deg <= 0 or inputs.phi_prime_override_deg >= 60:
            raise BetaValidationError("Direct friction angle must be between 0 and 60 degrees.")

    warnings: list[str] = []
    if any(layer.n60 > 50 for layer in inputs.layers):
        warnings.append("FHWA beta-method guidance is primarily intended for cohesionless soils with N60 up to 50.")
    if any(layer.n60 > 100 for layer in inputs.layers):
        warnings.append("Mayne-Harris should be used with caution for N60 above 100.")
    if inputs.z_gwt > inputs.z_top_shaft + inputs.shaft_length:
        warnings.append("Groundwater is below the shaft tip; effective stress is being treated as total stress over the full shaft.")
    tip_depth = inputs.z_top_shaft + inputs.shaft_length
    running_depth = 0.0
    for layer in inputs.layers[:-1]:
        running_depth += layer.thickness
        if abs(running_depth - tip_depth) <= 0.01:
            warnings.append("Shaft tip is within 0.01 m of a layer boundary; base resistance uses the lower layer when available.")
            break

    return warnings
