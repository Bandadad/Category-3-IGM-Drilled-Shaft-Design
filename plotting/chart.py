"""Matplotlib plotting for the three-branched load-settlement response."""

from __future__ import annotations

from matplotlib import pyplot as plt

from core.models import CalculationResult, CurveResult


def show_curve_plot(curve: CurveResult, result: CalculationResult) -> None:
    """Show the three-branched load-settlement curve in a separate window."""

    settlements_mm = [value * 1000.0 for value in curve.settlements_m]
    break_mm = [value * 1000.0 for value in curve.segment_breaks_m]

    figure, axis = plt.subplots(figsize=(8.5, 5.5))
    axis.plot(curve.loads_kN, settlements_mm, color="#111111", linewidth=2.8)
    axis.axvline(
        result.q_design,
        color="#c62828",
        linewidth=2.0,
        linestyle="-",
    )

    axis.set_title("Three-Branched Load-Settlement Curve", fontsize=13, pad=14)
    axis.set_xlabel("Qt (kN)", fontsize=12, fontweight="bold", labelpad=10)
    axis.xaxis.set_label_position("top")
    axis.xaxis.tick_top()
    axis.tick_params(axis="x", bottom=False, top=True, labelbottom=False, labeltop=True, direction="in", pad=8, width=1.5)

    axis.set_ylabel("wt (mm)", fontsize=12, fontweight="bold", rotation=0, labelpad=28)
    axis.tick_params(axis="y", direction="in", pad=8, width=1.5)

    axis.invert_yaxis()
    axis.set_xlim(left=0.0)
    axis.set_ylim(max(settlements_mm), 0.0)
    axis.grid(True, axis="y", linestyle="-", linewidth=0.8, alpha=0.45)

    for spine in axis.spines.values():
        spine.set_linewidth(1.5)

    axis.annotate(
        "Segment 1",
        (result.qt1 * 0.40, break_mm[1] * 0.45),
        xytext=(0, -10),
        textcoords="offset points",
        color="#111111",
        bbox=_annotation_box(),
    )
    axis.annotate(
        "Segment 2",
        ((result.qt1 + result.qtotal) * 0.5, (break_mm[1] + break_mm[2]) * 0.5),
        xytext=(10, -6),
        textcoords="offset points",
        color="#111111",
        bbox=_annotation_box(),
    )
    axis.annotate(
        "Segment 3",
        (result.qtotal, (break_mm[2] + break_mm[3]) * 0.5),
        xytext=(-78, -12),
        textcoords="offset points",
        color="#111111",
        ha="right",
        bbox=_annotation_box(),
    )
    axis.annotate(
        f"Design = {result.q_design:.1f} kN",
        (result.q_design, settlements_mm[-1] * 0.18),
        xytext=(10, 12),
        textcoords="offset points",
        color="#c62828",
        rotation=90,
        va="bottom",
        bbox=_annotation_box(edgecolor="#c62828"),
    )

    figure.tight_layout()
    plt.show()


def _annotation_box(edgecolor: str = "#d0d7de") -> dict[str, object]:
    """Return a light annotation box to keep labels readable above the plot."""

    return {
        "boxstyle": "round,pad=0.2",
        "facecolor": "white",
        "edgecolor": edgecolor,
        "linewidth": 0.6,
        "alpha": 0.95,
    }
