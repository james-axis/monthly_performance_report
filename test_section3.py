"""
Section 3: How You Compare – Licensee Benchmarking
Matches Sonny's layout: percentile bar, comparison table, histogram
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
import report_config as cfg
from reportlab.platypus import Paragraph

W, H = A4
MARGIN_L = 28 * mm
MARGIN_R = 28 * mm
USABLE_W = W - MARGIN_L - MARGIN_R

NAVY = "#181D27"
BLUE_BAR = "#414651"
GREEN_BAR = "#252B37"   # dark blue (adviser highlight)
GOLD_LINE = "#717680"
GREY_TEXT = "#717680"
BODY_TEXT = "#535862"
TABLE_HEADER_BG = "#181D27"
TABLE_ALT_ROW = "#F5F5F5"
GREEN_TEXT = "#181D27"  # navy for adviser values
BLUE_TEXT = "#414651"

# Data from config
ADVISER_CONV = cfg.ADVISER_CONV
ADVISER_LEADS = cfg.ADVISER_LEADS
ADVISER_RANK = cfg.ADVISER_RANK
TOTAL_PRACTICES = cfg.TOTAL_PRACTICES
PERCENTILE = cfg.PERCENTILE
NETWORK_AVG = cfg.NETWORK_AVG
MEDIAN = cfg.MEDIAN
TOP_QUARTILE = cfg.TOP_QUARTILE

# Histogram data from config
HIST_DATA = cfg.HIST_DATA


def build_histogram(output_path, adviser_conv, median, network_avg):
    """Histogram showing where all practices sit."""
    bins = list(HIST_DATA.keys())
    counts = list(HIST_DATA.values())
    x = np.arange(len(bins))

    # Find which bin the adviser falls in
    adviser_bin = None
    for i, b in enumerate(bins):
        if b.endswith("+"):
            lo = int(b.replace("+", ""))
            if adviser_conv >= lo:
                adviser_bin = i
        else:
            lo, hi = map(int, b.split("-"))
            if lo <= adviser_conv < hi:
                adviser_bin = i

    bar_colors = [BLUE_BAR] * len(bins)
    if adviser_bin is not None:
        bar_colors[adviser_bin] = GREEN_BAR

    fig, ax = plt.subplots(figsize=(8, 3.8))
    bars = ax.bar(x, counts, color=bar_colors, width=0.85, zorder=3)

    # Median and avg lines
    # Map percentages to bin positions
    def pct_to_x(pct):
        for i, b in enumerate(bins):
            if b.endswith("+"):
                lo = int(b.replace("+", ""))
                if pct >= lo:
                    return i + (pct - lo) / 5 * 0.5
            else:
                lo, hi = map(int, b.split("-"))
                if lo <= pct < hi:
                    return i + (pct - lo) / (hi - lo)
        return len(bins) - 1

    med_x = pct_to_x(median)
    avg_x = pct_to_x(network_avg)
    adv_x = pct_to_x(adviser_conv)

    ax.axvline(x=med_x, color="#A4A7AE", linestyle="--", linewidth=2.0, alpha=0.9, zorder=4)
    ax.text(med_x, max(counts) + 0.8, f"Median\n{median:.0f}%",
            ha="center", fontsize=8, color="#A4A7AE", fontweight="bold")

    ax.axvline(x=avg_x, color="#A4A7AE", linestyle="-.", linewidth=2.0, alpha=0.9, zorder=4)
    ax.text(avg_x + 0.3, max(counts) + 0.8, f"Network Avg\n{network_avg:.1f}%",
            ha="left", fontsize=8, color="#A4A7AE", fontweight="bold")

    # Adviser marker with arrow
    if adviser_bin is not None:
        ax.annotate(f"(#{cfg.ADVISER_RANK} of {cfg.TOTAL_PRACTICES})",
                    xy=(adv_x, counts[adviser_bin]),
                    xytext=(adv_x + 1.5, counts[adviser_bin] + 5),
                    fontsize=8, fontweight="bold", color="#181D27",
                    arrowprops=dict(arrowstyle="->", color="#181D27", lw=1.5))

    ax.set_xticks(x)
    ax.set_xticklabels([b.replace("-", "–") for b in bins], fontsize=7.5)
    ax.set_xlabel("New Lead to Completed Rate (%)", fontsize=9)
    ax.set_ylabel("Number of Practices", fontsize=9)
    ax.set_title(f"Where You Sit – New Lead to Completed Rate Across {cfg.TOTAL_PRACTICES} Active Practices",
                 fontsize=10.5, fontweight="bold", color=NAVY, pad=15)
    ax.tick_params(axis="both", labelsize=8)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    plt.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def draw_percentile_bar(c, x, y, w, h, adviser_pct, breakpoints, labels):
    """Draw the horizontal percentile bar with 4 segments."""
    # Segment colours (light to dark)
    seg_colors = ["#F5F5F5", "#E9EAEB", "#D5D7DA", "#A4A7AE"]
    n = len(labels)
    seg_w = w / n

    for i in range(n):
        sx = x + i * seg_w
        c.setFillColor(colors.HexColor(seg_colors[i]))
        c.setStrokeColor(colors.HexColor("#D5D7DA"))
        c.setLineWidth(0.5)
        c.rect(sx, y, seg_w, h, fill=1, stroke=1)

        # Label inside segment
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#535862"))
        c.drawCentredString(sx + seg_w / 2, y + h / 2 - 3, labels[i])

    # Breakpoint labels below
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    bp_labels = ["0–8%", "6%", "13%", "21%", "48%+"]
    positions = [x, x + seg_w, x + 2 * seg_w, x + 3 * seg_w, x + w]
    for i, (pos, lbl) in enumerate(zip(positions, bp_labels)):
        if i == 0:
            c.drawString(pos, y - 4 * mm, lbl)
        elif i == len(positions) - 1:
            c.drawRightString(pos, y - 4 * mm, lbl)
        else:
            c.drawCentredString(pos, y - 4 * mm, lbl)

    # Adviser marker (triangle) at their PERCENTILE position (not conversion %)
    # 99th percentile = 99% across the bar
    marker_x = x + (PERCENTILE / 100) * w
    marker_x = min(marker_x, x + w - 3)
    # Draw green triangle
    c.setFillColor(colors.HexColor("#252B37"))
    path = c.beginPath()
    path.moveTo(marker_x - 3 * mm, y - 1 * mm)
    path.lineTo(marker_x + 3 * mm, y - 1 * mm)
    path.lineTo(marker_x, y + 2 * mm)
    path.close()
    c.drawPath(path, fill=1, stroke=0)

    # "YOU: Top X%" label
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#252B37"))
    pctl_text = "Top 1%" if PERCENTILE >= 99 else f"Top {100 - PERCENTILE}%"
    c.drawString(x + w + 4 * mm, y + h / 2 - 3, f"YOU: {pctl_text}")


def draw_section3(output_path):
    c = canvas.Canvas(output_path, pagesize=A4)


    # Section heading
    y = H - 28 * mm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(NAVY))
    c.drawString(MARGIN_L, y, "3. How You Compare – Licensee Benchmarking")

    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E9EAEB"))
    c.setLineWidth(0.3)
    c.line(MARGIN_L, y, W - MARGIN_R, y)

    # Intro text
    y -= 6 * mm
    intro_style = ParagraphStyle("intro", fontName="Helvetica", fontSize=10,
                                  leading=14, textColor=colors.HexColor(BODY_TEXT))
    intro = Paragraph(
        "Here's how your numbers stack up against the full SLG network. "
        f"This comparison covers all {cfg.TOTAL_PRACTICES} active practices from {cfg.BENCH_PERIOD}. "
        "All other practices are shown anonymously.", intro_style)
    pw, ph = intro.wrap(USABLE_W, 100)
    intro.drawOn(c, MARGIN_L, y - ph)
    y -= ph + 8 * mm

    # "Your Percentile Ranking Across 85 Practices" subtitle
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor(BLUE_TEXT))
    c.drawCentredString(W / 2, y, f"Your Percentile Ranking Across {cfg.TOTAL_PRACTICES} Practices")
    y -= 12 * mm

    # Percentile bar
    bar_w = USABLE_W * 0.75
    bar_x = MARGIN_L + 5 * mm
    bar_h = 10 * mm
    draw_percentile_bar(c, bar_x, y, bar_w, bar_h, ADVISER_CONV,
                        [8, 13, 21, 48],
                        ["Bottom 25%", "25th–50th", "50th–75th", "Top 25%"])

    y -= 10 * mm

    # ── Comparison table ──
    col_widths = [USABLE_W * 0.20, USABLE_W * 0.20, USABLE_W * 0.20,
                  USABLE_W * 0.20, USABLE_W * 0.20]
    row_h = 8 * mm
    table_x = MARGIN_L

    # Header
    c.setFillColor(colors.HexColor(TABLE_HEADER_BG))
    c.rect(table_x, y - row_h, USABLE_W, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    headers = ["Metric", f"You ({cfg.PRACTICE_NAME})", "Network Average", "Median Practice", "Top Quartile"]
    cx = table_x
    for i, h in enumerate(headers):
        if i == 0:
            c.drawString(cx + 3 * mm, y - row_h + 2.5 * mm, h)
        else:
            c.drawCentredString(cx + col_widths[i] / 2, y - row_h + 2.5 * mm, h)
        cx += col_widths[i]
    y -= row_h

    # Data rows
    rows = [
        ("New Lead to Completed", f"{ADVISER_CONV}%", f"{NETWORK_AVG}%", f"{MEDIAN:.0f}%", f"{TOP_QUARTILE:.0f}%+"),
        ("Lead Volume", str(ADVISER_LEADS), "40", "—", "—"),
        ("Network Rank", f"#{ADVISER_RANK} of {TOTAL_PRACTICES}", "—", f"#{TOTAL_PRACTICES // 2}", f"Top {TOTAL_PRACTICES // 4}"),
        ("Percentile", f"{PERCENTILE}th", "—", "50th", "75th+"),
    ]
    for i, row in enumerate(rows):
        row_y = y - row_h
        if i % 2 == 1:
            c.setFillColor(colors.HexColor(TABLE_ALT_ROW))
            c.rect(table_x, row_y, USABLE_W, row_h, fill=1, stroke=0)

        cx = table_x
        for j, val in enumerate(row):
            if j == 0:
                c.setFont("Helvetica", 9)
                c.setFillColor(colors.HexColor(BODY_TEXT))
                c.drawString(cx + 3 * mm, row_y + 2.5 * mm, val)
            elif j == 1:
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(colors.HexColor(GREEN_TEXT))
                c.drawCentredString(cx + col_widths[j] / 2, row_y + 2.5 * mm, val)
            else:
                c.setFont("Helvetica", 9)
                c.setFillColor(colors.HexColor(BODY_TEXT))
                c.drawCentredString(cx + col_widths[j] / 2, row_y + 2.5 * mm, val)
            cx += col_widths[j]
        y -= row_h

    # ── Narrative paragraph
    y -= 8 * mm
    narr_style = ParagraphStyle("narr", fontName="Helvetica", fontSize=10,
                                 leading=14, textColor=colors.HexColor(BODY_TEXT))
    narr = Paragraph(
        f"<b>You rank #{ADVISER_RANK} out of {TOTAL_PRACTICES} active practices for new lead to completed rate</b> "
        f"and you're doing it at high volume ({ADVISER_LEADS} leads). Most practices with high "
        f"conversion rates are operating on much smaller lead counts. The median practice in "
        f"the network converts at {MEDIAN:.0f}% – you're converting at nearly "
        f"{ADVISER_CONV / MEDIAN:.0f}x that rate.", narr_style)
    pw, ph = narr.wrap(USABLE_W, 100)
    narr.drawOn(c, MARGIN_L, y - ph)
    y -= ph + 8 * mm

    # ── Histogram chart
    chart_path = output_path.replace(".pdf", "_hist.png")
    build_histogram(chart_path, ADVISER_CONV, MEDIAN, NETWORK_AVG)

    chart_h = 60 * mm
    c.drawImage(chart_path, MARGIN_L, y - chart_h, width=USABLE_W, height=chart_h,
                preserveAspectRatio=True, anchor="nw")
    y -= chart_h + 6 * mm

    # Bottom narrative
    bottom_style = ParagraphStyle("bottom", fontName="Helvetica-Oblique", fontSize=10,
                                   leading=14, textColor=colors.HexColor(BODY_TEXT))
    if ADVISER_RANK == 1:
        position_text = f"You sit at the very top of the network – no other practice converts at a higher rate."
    elif ADVISER_RANK <= 5:
        position_text = (f"Your position at {ADVISER_CONV}% puts you in rare company – "
                         f"only {ADVISER_RANK - 1} other practice{'s' if ADVISER_RANK > 2 else ''} convert at a higher rate.")
    else:
        position_text = f"Your position at {ADVISER_CONV}% puts you in the top {100 - PERCENTILE}% of the network."
    bottom = Paragraph(
        f"The distribution above shows where all {TOTAL_PRACTICES} practices sit. The majority of "
        f"practices are converting below 20%. {position_text} "
        f"You rank #{ADVISER_RANK} out of {TOTAL_PRACTICES} active practices.",
        bottom_style)
    pw, ph = bottom.wrap(USABLE_W, 100)
    bottom.drawOn(c, MARGIN_L, y - ph)

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W / 2, 18 * mm, f"SLG | Axis CRM Intelligence | Page 3 of {cfg.TOTAL_PAGES} | Version 1.0.0")

    c.save()
    if os.path.exists(chart_path):
        os.remove(chart_path)
    return output_path


if __name__ == "__main__":
    os.makedirs("/home/claude/adviser-monthly-reports/output", exist_ok=True)
    path = draw_section3("/home/claude/adviser-monthly-reports/output/section3_sample.pdf")
    print(f"✅ {path} ({os.path.getsize(path) / 1024:.0f} KB)")
