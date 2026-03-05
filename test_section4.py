"""
Section 4: Referral Partner Performance
Primary chart: grouped by organisation (PARTNER_GROUPS)
Secondary table: individual breakdown with Group column
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
import report_config as cfg

W, H = A4
MARGIN_L = 28 * mm
MARGIN_R = 28 * mm
USABLE_W = W - MARGIN_L - MARGIN_R

NAVY = "#181D27"
BLUE_BAR = "#414651"
GREEN_BAR = "#252B37"
GOLD_BAR = "#717680"
LIGHT_BAR = "#D5D7DA"
GREY_TEXT = "#717680"
BODY_TEXT = "#535862"
TABLE_HEADER_BG = "#181D27"
TABLE_ALT_ROW = "#F5F5F5"

PARTNER_GROUPS = cfg.PARTNER_GROUPS
PARTNERS = cfg.PARTNERS


def clip_str(text, max_pts, font_name="Helvetica", font_size=8.5):
    if pdfmetrics.stringWidth(text, font_name, font_size) <= max_pts:
        return text
    ellipsis = "…"
    while text and pdfmetrics.stringWidth(text + ellipsis, font_name, font_size) > max_pts:
        text = text[:-1]
    return text + ellipsis


def build_group_chart(output_path, groups):
    """Dual horizontal bar chart: Volume (leads) | Conversion (%) by org group."""
    if not groups:
        return None

    names = [g["name"] for g in groups]
    leads = [g["leads"] for g in groups]
    convs = [g["conv"] for g in groups]
    n = len(names)

    # Wrap long names
    wrapped = []
    for name in names:
        if len(name) > 18:
            words = name.split()
            mid = len(words) // 2
            wrapped.append(" ".join(words[:mid]) + "\n" + " ".join(words[mid:]))
        else:
            wrapped.append(name)

    fig_h = max(3.2, n * 0.55 + 1.4)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, fig_h), sharey=True)
    fig.subplots_adjust(wspace=0.08)

    y = np.arange(n)

    # Left: lead volume
    bars1 = ax1.barh(y, leads, color=BLUE_BAR, height=0.6, zorder=3)
    ax1.set_xlim(0, max(leads) * 1.3 if leads else 10)
    ax1.set_yticks(y)
    ax1.set_yticklabels(wrapped, fontsize=8)
    ax1.yaxis.set_ticks_position("none")
    for bar, v in zip(bars1, leads):
        ax1.text(v + 0.3, bar.get_y() + bar.get_height() / 2,
                 str(v), va="center", ha="left", fontsize=8, fontweight="bold", color=NAVY)
    ax1.set_xlabel("Leads (6 months)", fontsize=9)
    ax1.set_title("Volume", fontsize=11, fontweight="bold", color=NAVY, pad=10)
    ax1.grid(axis="x", alpha=0.15)
    ax1.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)

    # Right: conversion
    bar_colors = [GREEN_BAR if c >= 60 else GOLD_BAR if c >= 40 else LIGHT_BAR for c in convs]
    bars2 = ax2.barh(y, convs, color=bar_colors, height=0.6, zorder=3)
    ax2.set_xlim(0, 110)
    for bar, v in zip(bars2, convs):
        ax2.text(v + 1.5, bar.get_y() + bar.get_height() / 2,
                 f"{v}%", va="center", ha="left", fontsize=8, fontweight="bold", color=NAVY)
    ax2.set_xlabel("Conversion Rate (%)", fontsize=9)
    ax2.set_title("Conversion", fontsize=11, fontweight="bold", color=NAVY, pad=10)
    ax2.grid(axis="x", alpha=0.15)
    ax2.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax2.spines[spine].set_visible(False)

    ax1.invert_yaxis()
    fig.suptitle("Referral Partner Performance by Organisation (Last 6 Months)",
                 fontsize=11, fontweight="bold", color=NAVY, y=1.01)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def draw_section4(output_path):
    c = canvas.Canvas(output_path, pagesize=A4)

    # Section heading
    y = H - 28 * mm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(NAVY))
    c.drawString(MARGIN_L, y, "4. Referral Partner Performance")

    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E9EAEB"))
    c.setLineWidth(0.3)
    c.line(MARGIN_L, y, W - MARGIN_R, y)

    if not PARTNER_GROUPS:
        # No data — show placeholder
        y -= 10 * mm
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(colors.HexColor(BODY_TEXT))
        c.drawString(MARGIN_L, y, "No referral partner data found for the last 6 months.")
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor(GREY_TEXT))
        c.drawCentredString(W / 2, 18 * mm, f"SLG | Axis CRM Intelligence | Page 4 of {cfg.TOTAL_PAGES} | Version 1.0.0")
        c.save()
        return output_path

    # ── Primary chart: by organisation group ──
    y -= 5 * mm
    chart_path = output_path.replace(".pdf", "_chart.png")
    build_group_chart(chart_path, PARTNER_GROUPS)

    # Dynamically size chart height based on number of groups
    n_groups = len(PARTNER_GROUPS)
    chart_h = max(52, n_groups * 9 + 24) * mm
    c.drawImage(chart_path, MARGIN_L - 5 * mm, y - chart_h,
                width=USABLE_W + 10 * mm, height=chart_h,
                preserveAspectRatio=True, anchor="nw")
    y -= chart_h + 6 * mm

    # ── Individual breakdown table ──
    # Columns: Name (30%), Group (28%), Leads (10%), Apps (10%), Prem (12%), Conv (10%)
    col_widths = [USABLE_W * 0.30, USABLE_W * 0.28, USABLE_W * 0.10,
                  USABLE_W * 0.10, USABLE_W * 0.12, USABLE_W * 0.10]
    row_h = 7 * mm
    table_x = MARGIN_L

    # Table heading
    sub_style = ParagraphStyle("sub", fontName="Helvetica-Bold", fontSize=10,
                                leading=13, textColor=colors.HexColor(NAVY))
    sub = Paragraph("Individual Breakdown", sub_style)
    sw, sh = sub.wrap(USABLE_W, 20)
    sub.drawOn(c, MARGIN_L, y - sh)
    y -= sh + 3 * mm

    # Header row
    c.setFillColor(colors.HexColor(TABLE_HEADER_BG))
    c.rect(table_x, y - row_h, USABLE_W, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    headers = ["Name", "Group / Organisation", "Leads", "Apps", "Premium", "Conv."]
    cx = table_x
    for i, h in enumerate(headers):
        if i <= 1:
            c.drawString(cx + 2.5 * mm, y - row_h + 2.2 * mm, h)
        else:
            c.drawCentredString(cx + col_widths[i] / 2, y - row_h + 2.2 * mm, h)
        cx += col_widths[i]
    y -= row_h

    # Data rows — sorted by group then leads desc
    sorted_partners = sorted(PARTNERS, key=lambda p: (p["group"], -p["leads"]))

    for i, p in enumerate(sorted_partners):
        # Page break check (leave room for footer)
        if y - row_h < 28 * mm:
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.HexColor(GREY_TEXT))
            c.drawCentredString(W / 2, 18 * mm,
                                f"SLG | Axis CRM Intelligence | Page 4 of {cfg.TOTAL_PAGES} | Version 1.0.0")
            c.showPage()
            y = H - 28 * mm
            # Repeat header
            c.setFillColor(colors.HexColor(TABLE_HEADER_BG))
            c.rect(table_x, y - row_h, USABLE_W, row_h, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8.5)
            cx = table_x
            for j, h in enumerate(headers):
                if j <= 1:
                    c.drawString(cx + 2.5 * mm, y - row_h + 2.2 * mm, h)
                else:
                    c.drawCentredString(cx + col_widths[j] / 2, y - row_h + 2.2 * mm, h)
                cx += col_widths[j]
            y -= row_h

        row_y = y - row_h
        if i % 2 == 1:
            c.setFillColor(colors.HexColor(TABLE_ALT_ROW))
            c.rect(table_x, row_y, USABLE_W, row_h, fill=1, stroke=0)

        prem_str = f"${p['prem']:,}" if p["prem"] else "—"
        is_high_conv = p["conv"] >= 60
        padding = 3 * mm

        vals = [
            clip_str(p["name"], col_widths[0] - padding),
            clip_str(p["group"], col_widths[1] - padding),
            str(p["leads"]),
            str(p["apps"]),
            clip_str(prem_str, col_widths[4] - padding),
            f"{p['conv']}%",
        ]

        cx = table_x
        for j, val in enumerate(vals):
            if j <= 1:
                c.setFont("Helvetica", 8.5)
                c.setFillColor(colors.HexColor(BODY_TEXT))
                c.drawString(cx + 2.5 * mm, row_y + 2.2 * mm, val)
            elif j == 5 and is_high_conv:
                c.setFont("Helvetica-Bold", 8.5)
                c.setFillColor(colors.HexColor(NAVY))
                c.drawCentredString(cx + col_widths[j] / 2, row_y + 2.2 * mm, val)
            else:
                c.setFont("Helvetica", 8.5)
                c.setFillColor(colors.HexColor(BODY_TEXT))
                c.drawCentredString(cx + col_widths[j] / 2, row_y + 2.2 * mm, val)
            cx += col_widths[j]
        y -= row_h

    # ── Narrative ──
    y -= 6 * mm
    narr_style = ParagraphStyle("narr", fontName="Helvetica", fontSize=10,
                                 leading=14, textColor=colors.HexColor(BODY_TEXT))
    top = PARTNER_GROUPS[0]
    high_conv_groups = [g for g in PARTNER_GROUPS if g["conv"] >= 60]
    if high_conv_groups:
        hc_names = " and ".join(g["name"] for g in high_conv_groups[:2])
        conv_note = f" {hc_names} show the highest conversion rates."
    else:
        best_conv = max(PARTNER_GROUPS, key=lambda g: g["conv"])
        conv_note = f" {best_conv['name']} has the strongest conversion at {best_conv['conv']}%."

    narr_text = (
        f"<b>{top['name']}</b> is your dominant referral source by volume — "
        f"{top['leads']} leads with a {top['conv']}% conversion rate and "
        f"${top['prem']:,} in submitted premium over the last 6 months."
        f"{conv_note}"
    )
    narr = Paragraph(narr_text, narr_style)
    pw, ph = narr.wrap(USABLE_W, 60)
    if y - ph < 28 * mm:
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor(GREY_TEXT))
        c.drawCentredString(W / 2, 18 * mm,
                            f"SLG | Axis CRM Intelligence | Page 4 of {cfg.TOTAL_PAGES} | Version 1.0.0")
        c.showPage()
        y = H - 28 * mm
    narr.drawOn(c, MARGIN_L, y - ph)

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W / 2, 18 * mm,
                        f"SLG | Axis CRM Intelligence | Page 4 of {cfg.TOTAL_PAGES} | Version 1.0.0")

    c.save()
    if chart_path and os.path.exists(chart_path):
        os.remove(chart_path)
    return output_path


if __name__ == "__main__":
    os.makedirs("/home/claude/adviser-monthly-reports/output", exist_ok=True)
    path = draw_section4("/home/claude/adviser-monthly-reports/output/section4_sample.pdf")
    print(f"✅ {path} ({os.path.getsize(path) / 1024:.0f} KB)")
