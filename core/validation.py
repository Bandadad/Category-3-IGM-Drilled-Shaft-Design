"""Input validation for the Mayne-Harris draft calculator."""

from __future__ import annotations

from dataclasses import fields

from .models import CalculationInput


class ValidationError(ValueError):
    """Raised when user inputs are not physically or numerically acceptable."""


def validate_inputs(inputs: CalculationInput) -> list[str]:
    """Validate input ranges and return non-fatal warning messages."""

    if inputs.gamma <= 0:
        raise ValidationError("Unit weight must be positive.")
    if inputs.diameter <= 0:
        raise ValidationError("Shaft diameter must be positive.")
    if inputs.socket_length <= 0:
        raise ValidationError("Socket length must be positive.")
    if inputs.n60 <= 0:
        raise ValidationError("N60 must be positive.")
    if inputs.nu < 0.0 or inputs.nu >= 0.5:
        raise ValidationError("Poisson's ratio must be between 0.0 and 0.5.")
    if inputs.z_top_socket < 0:
        raise ValidationError("Depth to top of socket cannot be negative.")
    if inputs.z_gwt < 0:
        raise ValidationError("Groundwater depth cannot be negative.")
    if inputs.branch3_extension_mm <= 0:
        raise ValidationError("Branch 3 plot extension must be positive.")
    if inputs.points_per_segment < 2:
        raise ValidationError("Plot discretization must be at least 2 points per segment.")

    optional_positive_fields = {
        "sigma_vo_eff_mid_override": "Direct mid-depth effective stress",
        "sigma_vo_eff_tip_override": "Direct tip effective stress",
        "esl_override": "EsL override",
        "esm_override": "Esm override",
        "eb_override": "Eb override",
        "ec_override": "Ec override",
        "su_override": "su override",
        "atmospheric_pressure": "Atmospheric pressure",
    }
    for field in fields(inputs):
        value = getattr(inputs, field.name)
        if field.name in optional_positive_fields and value is not None and value <= 0:
            raise ValidationError(f"{optional_positive_fields[field.name]} must be positive.")

    if inputs.phi_prime_override_deg is not None:
        if inputs.phi_prime_override_deg <= 0 or inputs.phi_prime_override_deg >= 60:
            raise ValidationError("Direct friction angle must be between 0 and 60 degrees.")

    if inputs.k0_override is not None and inputs.k0_override <= 0:
        raise ValidationError("Direct K0 must be positive.")

    warnings: list[str] = []
    if inputs.n60 < 50:
        warnings.append("Mayne-Harris correlations are primarily intended for N60 values near 50 to 100.")
    if inputs.n60 > 100:
        warnings.append("Mayne-Harris should be used with caution for N60 above 100.")
    if inputs.z_gwt > inputs.z_top_socket + inputs.socket_length:
        warnings.append("Groundwater is below the socket tip; effective stress is being treated as total stress over the full socket.")

    return warnings
