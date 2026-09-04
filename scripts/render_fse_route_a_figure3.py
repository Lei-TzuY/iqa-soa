#!/usr/bin/env python3
"""Render FSE 2027 Route-A manuscript Figure 3 from declared execution labels.

Figure 3 shows the three governance treatment families and, critically, which of
them was actually realized under a real model in this paper. Exactly one was:
the QA OFF qualification path. PARTIAL QA and QA FULL are implemented and
exercised deterministically, but no real-model execution of either exists, and
the QA FULL versus QA OFF confirmatory contrast was never entered.

The v0.7 figure drew all three lanes identically, converging on a shared
"Metrics" node. That is a presentation defect: a reader can reasonably infer
that all three lanes produced real-model measurements. This script encodes the
execution status of each lane as an explicit visual property (stroke weight,
stroke style, fill, and a status badge) so the executed path cannot be confused
with the unexecuted ones.

This script reads no result file, contacts no provider, performs no inference,
and derives nothing from evidence rows. Every label below is a declared
constant, mirroring the manuscript's frozen scientific state:

    successor QA-OFF qualification .... 102/102 observed, 0 retries,
                                        3 invalidated, 7/17 task roles qualified,
                                        terminal SCHEDULE_COMPLETE_VERDICT_HOLD
    confirmatory eligibility ......... NO
    confirmatory execution ........... NOT ENTERED

Usage:
    python scripts/render_fse_route_a_figure3.py --out build/figures/fse_route_a_figure3.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

# --- declared, non-derived figure content -----------------------------------

FIGURE_WIDTH_IN = 6.85
FIGURE_HEIGHT_IN = 2.62
FIGURE_DPI = 320

EXECUTED_EDGE = "#111111"
EXECUTED_FILL = "#e8eef7"
EXECUTED_TEXT = "#111111"
PLANNED_EDGE = "#8a8a8a"
PLANNED_FILL = "#ffffff"
PLANNED_TEXT = "#5f5f5f"
BLOCKED_EDGE = "#111111"
BLOCKED_FILL = "#f2f2f2"

LANE_Y = {"off": 2.70, "partial": 1.62, "full": 0.54}

# Each lane: (key, treatment label, run-stage label, terminal label, status badge)
LANES = (
    (
        "off",
        "QA OFF\nminimal observation",
        "Real-model qualification\n17 tasks x 2 arms x 3 seeds\n102 cells, executed once",
        "Verdict HOLD\n102/102 observed, 0 retries\n3 invalidated, 7/17 roles",
        "EXECUTED IN THIS PAPER",
    ),
    (
        "partial",
        "PARTIAL QA\npermission + budget",
        "No real-model execution",
        "No measurements\nproduced",
        "IMPLEMENTED - NOT EXECUTED UNDER A REAL MODEL",
    ),
    (
        "full",
        "QA FULL\nfull governance chain",
        "No real-model execution",
        "No measurements\nproduced",
        "IMPLEMENTED - PROSPECTIVELY SPECIFIED CONFIRMATORY PATH - NOT EXECUTED",
    ),
)

SOURCE_LABEL = "Frozen candidate,\nbenchmark, policy,\nprovider + seed"
GATE_LABEL = "Confirmatory\ngate CLOSED\n(eligibility: no)"
SINK_LABEL = "QA FULL vs QA OFF\neffect estimate\nNOT PRODUCED"

CAPTION_NOTE = (
    "Solid lane = executed under a real model. Dashed lanes = implemented and "
    "exercised deterministically only; no real-model evidence exists for them."
)

COL_X = {"treat": 2.85, "run": 5.05, "term": 7.25}
BOX_W = {"treat": 1.62, "run": 1.92, "term": 1.92}
BOX_H = 0.58


def _box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    executed: bool,
    fill: str | None = None,
    edge: str | None = None,
    fontsize: float = 5.6,
    weight: str = "normal",
) -> None:
    """Draw one node. Execution status drives stroke weight, style and colour."""

    patch = mpatches.FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.014,rounding_size=0.035",
        linewidth=1.5 if executed else 0.9,
        linestyle="solid" if executed else (0, (3.2, 2.0)),
        edgecolor=edge or (EXECUTED_EDGE if executed else PLANNED_EDGE),
        facecolor=fill or (EXECUTED_FILL if executed else PLANNED_FILL),
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=EXECUTED_TEXT if executed else PLANNED_TEXT,
        fontweight=weight,
        linespacing=1.35,
        zorder=3,
    )


def _arrow(ax, x0: float, y0: float, x1: float, y1: float, *, executed: bool) -> None:
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops={
            "arrowstyle": "-|>,head_width=0.13,head_length=0.28",
            "linewidth": 1.4 if executed else 0.85,
            "linestyle": "solid" if executed else (0, (3.2, 2.0)),
            "color": EXECUTED_EDGE if executed else PLANNED_EDGE,
            "shrinkA": 1.0,
            "shrinkB": 1.0,
        },
        zorder=1,
    )


def render(out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_IN, FIGURE_HEIGHT_IN))
    # Fill the whole figure: the default axes inset shrinks data units relative
    # to the fixed point size of the labels and overflows the node boxes.
    ax.set_position((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0, 10.0)
    ax.set_ylim(0, 3.34)
    ax.axis("off")

    # Source node.
    _box(ax, 0.80, 1.62, 1.42, 0.90, SOURCE_LABEL, executed=True, fontsize=5.4)

    for key, treat, run, term, badge in LANES:
        y = LANE_Y[key]
        executed = key == "off"

        _arrow(ax, 1.51, 1.62, COL_X["treat"] - BOX_W["treat"] / 2, y, executed=executed)
        _box(ax, COL_X["treat"], y, BOX_W["treat"], BOX_H, treat, executed=executed)
        _arrow(
            ax,
            COL_X["treat"] + BOX_W["treat"] / 2,
            y,
            COL_X["run"] - BOX_W["run"] / 2,
            y,
            executed=executed,
        )
        _box(ax, COL_X["run"], y, BOX_W["run"], BOX_H, run, executed=executed)
        _arrow(
            ax,
            COL_X["run"] + BOX_W["run"] / 2,
            y,
            COL_X["term"] - BOX_W["term"] / 2,
            y,
            executed=executed,
        )
        _box(ax, COL_X["term"], y, BOX_W["term"], BOX_H, term, executed=executed)

        # Status badge sits directly above its lane so it cannot be misread.
        ax.text(
            COL_X["treat"] - BOX_W["treat"] / 2,
            y + BOX_H / 2 + 0.155,
            badge,
            ha="left",
            va="center",
            fontsize=4.5,
            color=EXECUTED_EDGE if executed else PLANNED_TEXT,
            fontweight="bold" if executed else "normal",
            zorder=3,
        )

    # The executed lane terminates at a closed gate, not at a metrics node.
    _arrow(
        ax,
        COL_X["term"] + BOX_W["term"] / 2,
        LANE_Y["off"],
        8.62,
        2.02,
        executed=True,
    )
    _box(
        ax,
        9.15,
        1.62,
        1.45,
        0.90,
        GATE_LABEL,
        executed=True,
        fill=BLOCKED_FILL,
        edge=BLOCKED_EDGE,
        fontsize=5.4,
        weight="bold",
    )
    _arrow(ax, 9.15, 1.15, 9.15, 0.85, executed=False)
    _box(
        ax,
        9.15,
        0.54,
        1.45,
        0.58,
        SINK_LABEL,
        executed=False,
        fontsize=5.0,
    )

    ax.text(
        0.06,
        0.08,
        CAPTION_NOTE,
        ha="left",
        va="center",
        fontsize=4.8,
        color=PLANNED_TEXT,
        style="italic",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        out_path,
        dpi=FIGURE_DPI,
        bbox_inches="tight",
        pad_inches=0.02,
        facecolor="white",
    )
    plt.close(fig)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("build/figures/fse_route_a_figure3.png"),
        help="output PNG path",
    )
    args = parser.parse_args()
    written = render(args.out)
    print(f"wrote {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
