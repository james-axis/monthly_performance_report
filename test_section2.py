"""
Section 2: 12-Month Performance Trend
Chart + trailing average text + month-by-month table
Matches Sonny's layout: blue bars, gold app line, green current month, red dashed avg line
"""
import os
import calendar
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
import report_config as cfg

W, H = A4
MARGIN_L = 28 * mm
MARGIN_R = 28 * mm
USABLE_W = W - MARGIN_L - MARGIN_R

# Colours
NAVY = "#181D27"
BLUE_BAR = "#414651"
GREEN_BAR = "#252B37"   # dark blue (current month highlight)
GOLD_LINE = "#A4A7AE"   # light blue (app count line)
RED_AVG = "#717680"     # medium blue (trailing avg line)
GREY_TEXT = "#717680"
BODY_TEXT = "#535862"
TABLE_HEADER_BG = "#181D27"
TABLE_ALT_ROW = "#F5F5F5"
GREEN_HIGHLIGHT = "#F5F5F5"  # light blue highlight
GREEN_TEXT_DARK = "#181D27"  # navy for highlighted text

# Data from config
MONTHS_DATA = cfg.MONTHS_DATA


def build_trend_chart(output_path, months_data, current_month=2, current_year=2026):
    """Build the 12-month trend chart matching Sonny's exact style."""
    labels = []
    prems = []
    apps = []
    bar_colors = []

    for d in months_data:
        short_month = calendar.month_abbr[d["m"]]
        yr_short = str(d["y"])[2:]  # e.g. '25', '26'
        labels.append(f"{short_month}\n'{yr_short}")
        prems.append(d["prem"])
        apps.append(d["apps"])
        if d["m"] == current_month and d["y"] == current_year:
            bar_colors.append(GREEN_BAR)
        else:
            bar_colors.append(BLUE_BAR)

    avg_prem = sum(prems) / len(prems)

    fig, ax1 = plt.subplots(figsize=(10, 4.5))

    x = np.arange(len(labels))
    bar_width = 0.6

    # Premium bars
    bars = ax1.bar(x, [p / 1000 for p in prems], bar_width, color=bar_colors, zorder=3)

    # Trailing average dashed line (red)
    ax1.axhline(y=avg_prem / 1000, color=RED_AVG, linestyle="--", linewidth=1.2, alpha=0.7, zorder=2)
    # Label the avg line on right side
    ax1.text(len(labels) - 0.5, avg_prem / 1000 + 1, f"12m avg: ${avg_prem/1000:.0f}K",
             fontsize=7.5, color=RED_AVG, fontstyle="italic", ha="right", alpha=0.8)

    # Application count line on secondary axis
    ax2 = ax1.twinx()
    ax2.plot(x, apps, color=GOLD_LINE, marker="o", markersize=7, linewidth=2.2, zorder=5)

    # Star on current month's dot
    current_idx = len(labels) - 1
    ax2.plot(current_idx, apps[current_idx], marker="*", markersize=14,
             color="white", zorder=6)
    ax2.plot(current_idx, apps[current_idx], marker="*", markersize=11,
             color=GOLD_LINE, zorder=7)

    # Label select bars with value (high months: show $XK above bar)
    # Sonny labels: $64K on Sep, ~$78K on Dec, $101K on Feb
    for i, p in enumerate(prems):
        if p >= 60000:
            ax1.text(i, p / 1000 + 2, f"${p/1000:.0f}K",
                     ha="center", va="bottom", fontsize=8, fontweight="bold",
                     color=NAVY)

    # Axes formatting
    ax1.set_ylabel("Submitted Premium ($K)", fontsize=9, color=NAVY)
    ax2.set_ylabel("Applications", fontsize=9, color=GOLD_LINE, rotation=270, labelpad=15)

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_ylim(0, 120)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:.0f}K"))
    ax1.tick_params(axis="y", labelsize=8)

    ax2.set_ylim(0, 35)
    ax2.tick_params(axis="y", labelsize=8, colors=GOLD_LINE)

    ax1.set_title("12-Month Submitted Premium & Application Volume",
                  fontsize=11, fontweight="bold", color=NAVY, pad=12)

    ax1.grid(axis="y", alpha=0.15, zorder=0)
    ax1.set_axisbelow(True)

    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)
    ax2.spines["top"].set_visible(False)

    plt.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def draw_section2(output_path):
    """Build Section 2 page: month-by-month table only (chart is on page 1)."""
    c = canvas.Canvas(output_path, pagesize=A4)

    y = H - 28 * mm

    # ── Table: Month | Apps | Total Premium
    col_widths = [USABLE_W * 0.40, USABLE_W * 0.30, USABLE_W * 0.30]
    row_h = 7.5 * mm
    table_x = MARGIN_L

    # Header row
    c.setFillColor(colors.HexColor(TABLE_HEADER_BG))
    c.rect(table_x, y - row_h, USABLE_W, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(table_x + 4 * mm, y - row_h + 2.2 * mm, "Month")
    c.drawRightString(table_x + col_widths[0] + col_widths[1] - 4 * mm,
                      y - row_h + 2.2 * mm, "Apps")
    c.drawRightString(table_x + USABLE_W - 4 * mm,
                      y - row_h + 2.2 * mm, "Total Premium")
    y -= row_h

    # Data rows (Mar 2025 - Jan 2026 normal, Feb 2026 highlighted green)
    for i, d in enumerate(MONTHS_DATA):
        is_current = (d["m"] == 2 and d["y"] == 2026)
        row_y = y - row_h

        # Background
        if is_current:
            c.setFillColor(colors.HexColor(GREEN_HIGHLIGHT))
            c.rect(table_x, row_y, USABLE_W, row_h, fill=1, stroke=0)
        elif i % 2 == 1:
            c.setFillColor(colors.HexColor(TABLE_ALT_ROW))
            c.rect(table_x, row_y, USABLE_W, row_h, fill=1, stroke=0)

        # Text
        month_label = f"{calendar.month_abbr[d['m']]} {d['y']}"
        if is_current:
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(colors.HexColor(GREEN_TEXT_DARK))
        else:
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.HexColor(BODY_TEXT))

        c.drawString(table_x + 4 * mm, row_y + 2.2 * mm, month_label)
        c.drawRightString(table_x + col_widths[0] + col_widths[1] - 4 * mm,
                          row_y + 2.2 * mm, str(d["apps"]))
        c.drawRightString(table_x + USABLE_W - 4 * mm,
                          row_y + 2.2 * mm, f"${d['prem']:,}")

        y -= row_h

    # ── Footer
    y -= 6 * mm
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W / 2, 18 * mm, f"SLG CRM Intelligence Report  |  Page 2 of {cfg.TOTAL_PAGES}")

    c.save()

    return output_path


if __name__ == "__main__":
    os.makedirs("/home/claude/adviser-monthly-reports/output", exist_ok=True)
    path = draw_section2("/home/claude/adviser-monthly-reports/output/section2_sample.pdf")
    print(f"✅ {path} ({os.path.getsize(path) / 1024:.0f} KB)")
