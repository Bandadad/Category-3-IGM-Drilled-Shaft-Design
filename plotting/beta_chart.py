"""Matplotlib plotting for the beta-method three-branched response."""

from __future__ import annotations

from matplotlib import pyplot as plt

from core.beta_models import BetaCalculationResult, BetaCurveResult


def show_beta_curve_plot(curve: BetaCurveResult, result: BetaCalculationResult) -> None:
    """Show axial load on the x-axis and inverted settlement on the y-axis."""

    settlements_mm = [value * 1000.0 for value in curve.settlements_m]
    break_mm = [value * 1000.0 for value in curve.segment_breaks_m]
    design_capacity_mn = result.q_design / 1000.0
    loads_mn = [value / 1000.0 for value in curve.loads_kN]
    break_loads_mn = [value / 1000.0 for value in curve.segment_breaks_kN]

    figure, axis = plt.subplots(figsize=(8.5, 5.5))
    axis.plot(loads_mn, settlements_mm, color="#111111", linewidth=2.8)
    axis.scatter(
        [break_loads_mn[1], break_loads_mn[2]],
        [break_mm[1], break_mm[2]],
        color="#1c608f",
        zorder=3,
    )
    axis.vlines(design_capacity_mn, 0.0, max(settlements_mm), color="red", linestyle="--", linewidth=1.6)
    axis.text(
        design_capacity_mn + 0.05,
        max(settlements_mm),
        f"Design Load: {design_capacity_mn:.2f} MN",
        color="red",
        verticalalignment="bottom",
    )

    axis.set_title("Beta Method Three-Branched Load-Settlement Curve", fontsize=13, pad=14)
    axis.set_xlabel("Axial load, Qt (MN)", fontsize=12, fontweight="bold", labelpad=10)
    axis.xaxis.set_label_position("top")
    axis.xaxis.tick_top()
    axis.set_ylabel("Settlement, wt (mm)", fontsize=12, fontweight="bold", labelpad=10)
    axis.set_xlim(left=0.0)
    axis.set_ylim(0.0, max(settlements_mm) * 1.2 if settlements_mm else 1.0)
    axis.invert_yaxis()
    axis.grid(True, linestyle="-", linewidth=0.8, alpha=0.35)

    for spine in axis.spines.values():
        spine.set_linewidth(1.4)

    axis.annotate(
        "Segment 1",
        (break_loads_mn[1] * 0.45, break_mm[1] * 0.45),
        xytext=(0, 10),
        textcoords="offset points",
        bbox=_annotation_box(),
    )
    axis.annotate(
        "Segment 2",
        ((break_loads_mn[1] + break_loads_mn[2]) * 0.5, (break_mm[1] + break_mm[2]) * 0.5),
        xytext=(10, 10),
        textcoords="offset points",
        bbox=_annotation_box(),
    )
    axis.annotate(
        "Segment 3",
        ((break_loads_mn[2] + break_loads_mn[3]) * 0.5, (break_mm[2] + break_mm[3]) * 0.5),
        xytext=(10, -22),
        textcoords="offset points",
        bbox=_annotation_box(),
    )
    axis.annotate(
        f"Qt1 = {break_loads_mn[1]:.2f} MN\nwt1 = {break_mm[1]:.2f} mm",
        (break_loads_mn[1], break_mm[1]),
        xytext=(12, -10),
        textcoords="offset points",
        bbox=_annotation_box(edgecolor="#1c608f"),
    )
    axis.annotate(
        f"Qt,max = {break_loads_mn[2]:.2f} MN\nwt2 = {break_mm[2]:.2f} mm",
        (break_loads_mn[2], break_mm[2]),
        xytext=(12, 12),
        textcoords="offset points",
        bbox=_annotation_box(edgecolor="#1c608f"),
    )

    figure.tight_layout()
    plt.show()


def _annotation_box(edgecolor: str = "#d0d7de") -> dict[str, object]:
    """Return a light annotation box."""

    return {
        "boxstyle": "round,pad=0.2",
        "facecolor": "white",
        "edgecolor": edgecolor,
        "linewidth": 0.6,
        "alpha": 0.95,
    }
