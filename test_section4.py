"""
Section 4: Referral Partner Performance
Dual horizontal bar chart (Volume | Conversion) + detailed table + narrative
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
import report_config as cfg
from reportlab.platypus import Paragraph

W, H = A4
MARGIN_L = 28 * mm
MARGIN_R = 28 * mm
USABLE_W = W - MARGIN_L - MARGIN_R

NAVY = "#181D27"
BLUE_BAR = "#414651"
GREEN_BAR = "#252B37"   # dark blue (high conv)
GOLD_BAR = "#717680"    # medium blue (mid conv)
RED_BAR = "#D5D7DA"     # light blue (low conv)
GREY_TEXT = "#717680"
BODY_TEXT = "#535862"
TABLE_HEADER_BG = "#181D27"
TABLE_ALT_ROW = "#F5F5F5"
GREEN_TEXT = "#181D27"  # navy

# Data from config
PARTNERS = cfg.PARTNERS


def build_dual_bar_chart(output_path, partners):
    """Side-by-side horizontal bars: Volume (left) | Conversion (right)"""
    names = [p["name"] for p in partners]
    apps = [p["apps"] for p in partners]
    convs = [p["conv"] for p in partners]
    y = np.arange(len(names))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 4.2), sharey=True)
    fig.subplots_adjust(wspace=0.08)

    # Left: Volume (apps) - blue bars, left-to-right
    bars1 = ax1.barh(y, apps, color=BLUE_BAR, height=0.65, zorder=3)
    ax1.set_xlim(0, max(apps) * 1.25)
    ax1.set_yticks(y)
    ax1.set_yticklabels(names, fontsize=7.5)
    ax1.yaxis.set_ticks_position("none")
    
    for i, (bar, v) in enumerate(zip(bars1, apps)):
        ax1.text(v + 0.5, i, str(v), va="center", ha="left", fontsize=8, fontweight="bold", color=NAVY)
    
    ax1.set_xlabel("Applications (6 months)", fontsize=9)
    ax1.set_title("Volume", fontsize=11, fontweight="bold", color=NAVY, pad=10)
    ax1.grid(axis="x", alpha=0.15)
    ax1.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)

    # Right: Conversion - colored by threshold
    bar_colors = []
    for c in convs:
        if c >= 60:
            bar_colors.append(GREEN_BAR)
        elif c >= 40:
            bar_colors.append(GOLD_BAR)
        else:
            bar_colors.append(RED_BAR)

    bars2 = ax2.barh(y, convs, color=bar_colors, height=0.65, zorder=3)
    ax2.set_xlim(0, 105)
    
    for i, (bar, v) in enumerate(zip(bars2, convs)):
        ax2.text(v + 1.5, i, f"{v}%", va="center", ha="left", fontsize=8, fontweight="bold", color=NAVY)

    ax2.set_xlabel("Conversion Rate (%)", fontsize=9)
    ax2.set_title("Conversion", fontsize=11, fontweight="bold", color=NAVY, pad=10)
    ax2.grid(axis="x", alpha=0.15)
    ax2.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax2.spines[spine].set_visible(False)

    ax1.invert_yaxis()

    # Title
    fig.suptitle("Referral Partner Performance (Last 6 Months)",
                 fontsize=11.5, fontweight="bold", color=NAVY, y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.93])
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

    # Chart
    y -= 6 * mm
    chart_path = output_path.replace(".pdf", "_chart.png")
    build_dual_bar_chart(chart_path, PARTNERS)
    
    chart_h = 68 * mm
    c.drawImage(chart_path, MARGIN_L - 5*mm, y - chart_h, width=USABLE_W + 10*mm, height=chart_h,
                preserveAspectRatio=True, anchor="nw")
    y -= chart_h + 6 * mm

    # ── Table ──
    col_widths = [USABLE_W * 0.34, USABLE_W * 0.12, USABLE_W * 0.12, USABLE_W * 0.22, USABLE_W * 0.20]
    row_h = 8 * mm
    table_x = MARGIN_L

    # Header
    c.setFillColor(colors.HexColor(TABLE_HEADER_BG))
    c.rect(table_x, y - row_h, USABLE_W, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    headers = ["Referral Partner", "Leads", "Apps", "Quoted Prem.", "Conv."]
    cx = table_x
    for i, h in enumerate(headers):
        if i == 0:
            c.drawString(cx + 3 * mm, y - row_h + 2.5 * mm, h)
        else:
            c.drawCentredString(cx + col_widths[i] / 2, y - row_h + 2.5 * mm, h)
        cx += col_widths[i]
    y -= row_h

    # Data rows
    for i, p in enumerate(PARTNERS):
        row_y = y - row_h
        if i % 2 == 1:
            c.setFillColor(colors.HexColor(TABLE_ALT_ROW))
            c.rect(table_x, row_y, USABLE_W, row_h, fill=1, stroke=0)

        cx = table_x
        vals = [
            p["full"],
            str(p["leads"]),
            str(p["apps"]),
            f"${p['prem']:,}",
            f"{p['conv']}%"
        ]
        for j, val in enumerate(vals):
            if j == 0:
                c.setFont("Helvetica", 9)
                c.setFillColor(colors.HexColor(BODY_TEXT))
                c.drawString(cx + 3 * mm, row_y + 2.5 * mm, val)
            elif j == 4:  # Conv column - green highlight for high values
                if p["conv"] >= 60:
                    c.setFont("Helvetica-Bold", 9)
                    c.setFillColor(colors.HexColor(GREEN_TEXT))
                else:
                    c.setFont("Helvetica", 9)
                    c.setFillColor(colors.HexColor(BODY_TEXT))
                c.drawCentredString(cx + col_widths[j] / 2, row_y + 2.5 * mm, val)
            else:
                c.setFont("Helvetica", 9)
                c.setFillColor(colors.HexColor(BODY_TEXT))
                c.drawCentredString(cx + col_widths[j] / 2, row_y + 2.5 * mm, val)
            cx += col_widths[j]
        y -= row_h

    # ── Narrative ──
    y -= 8 * mm
    narr_style = ParagraphStyle("narr", fontName="Helvetica", fontSize=10,
                                 leading=14, textColor=colors.HexColor(BODY_TEXT))
    
    # Find dominant partner and highest converters
    top_vol = PARTNERS[0]
    high_conv = [p for p in PARTNERS if p["conv"] >= 60]
    high_conv_names = " and ".join([p["full"].split("–")[0].strip().split("(")[0].strip() for p in high_conv[:2]])
    
    narr_text = (
        f"<b>{top_vol['full']}</b> is your dominant source by volume – "
        f"{top_vol['leads']} leads with a {top_vol['conv']}% conversion. "
        f"Nectar provides breadth across multiple brokers. "
        f"{high_conv_names} show the highest conversion rates at 67%."
    )
    
    narr = Paragraph(narr_text, narr_style)
    pw, ph = narr.wrap(USABLE_W, 100)
    narr.drawOn(c, MARGIN_L, y - ph)

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W / 2, 18 * mm, f"SLG | Axis CRM Intelligence | Page 4 of {cfg.TOTAL_PAGES} | Version 1.0.0")

    c.save()
    if os.path.exists(chart_path):
        os.remove(chart_path)
    return output_path


if __name__ == "__main__":
    os.makedirs("/home/claude/adviser-monthly-reports/output", exist_ok=True)
    path = draw_section4("/home/claude/adviser-monthly-reports/output/section4_sample.pdf")
    print(f"✅ {path} ({os.path.getsize(path) / 1024:.0f} KB)")
