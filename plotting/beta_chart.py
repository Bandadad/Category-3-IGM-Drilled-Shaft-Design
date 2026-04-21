"""Matplotlib plotting for the beta-method three-branched response."""

from __future__ import annotations

from matplotlib import pyplot as plt

from core.beta_models import BetaCalculationResult, BetaCurveResult


def show_beta_curve_plot(curve: BetaCurveResult, result: BetaCalculationResult) -> None:
    """Show settlement on the x-axis and axial load on the y-axis."""

    settlements_mm = [value * 1000.0 for value in curve.settlements_m]
    break_mm = [value * 1000.0 for value in curve.segment_breaks_m]

    figure, axis = plt.subplots(figsize=(8.5, 5.5))
    axis.plot(settlements_mm, curve.loads_kN, color="#111111", linewidth=2.8)
    axis.scatter(
        [break_mm[1], break_mm[2]],
        [curve.segment_breaks_kN[1], curve.segment_breaks_kN[2]],
        color="#1c608f",
        zorder=3,
    )

    axis.set_title("Beta Method Three-Branched Load-Settlement Curve", fontsize=13, pad=14)
    axis.set_xlabel("Settlement, wt (mm)", fontsize=12, fontweight="bold", labelpad=10)
    axis.set_ylabel("Axial load, Qt (kN)", fontsize=12, fontweight="bold", labelpad=10)
    axis.set_xlim(left=0.0)
    axis.set_ylim(bottom=0.0)
    axis.grid(True, linestyle="-", linewidth=0.8, alpha=0.35)

    for spine in axis.spines.values():
        spine.set_linewidth(1.4)

    axis.annotate(
        "Segment 1",
        (break_mm[1] * 0.45, result.qt1 * 0.45),
        xytext=(0, 10),
        textcoords="offset points",
        bbox=_annotation_box(),
    )
    axis.annotate(
        "Segment 2",
        ((break_mm[1] + break_mm[2]) * 0.5, (result.qt1 + result.qtotal) * 0.5),
        xytext=(10, 10),
        textcoords="offset points",
        bbox=_annotation_box(),
    )
    axis.annotate(
        "Segment 3",
        ((break_mm[2] + break_mm[3]) * 0.5, result.qtotal),
        xytext=(10, -22),
        textcoords="offset points",
        bbox=_annotation_box(),
    )
    axis.annotate(
        f"Qt1 = {result.qt1:.1f} kN\nwt1 = {break_mm[1]:.2f} mm",
        (break_mm[1], result.qt1),
        xytext=(12, -10),
        textcoords="offset points",
        bbox=_annotation_box(edgecolor="#1c608f"),
    )
    axis.annotate(
        f"Qt,max = {result.qtotal:.1f} kN\nwt2 = {break_mm[2]:.2f} mm",
        (break_mm[2], result.qtotal),
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
