"""
Section 10: What Your Data Says Works
Two side-by-side charts: Call Activity conversion & Quoted vs Unquoted
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import report_config as cfg

W, H = A4
ML = 28 * mm
MR = 28 * mm
UW = W - ML - MR

NAVY = "#181D27"
GREY_TEXT = "#717680"
BODY_TEXT = "#535862"
BAR_BLUE = "#717680"
LINE_NAVY = "#181D27"


def make_charts(out_path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.0))
    fig.subplots_adjust(wspace=0.45, left=0.08, right=0.96, top=0.82, bottom=0.18)

    # ── Chart 1: Conversion by Call Activity ──
    labels = cfg.CALL_BUCKETS
    rates = cfg.CONV_BY_CALLS_12M
    # 12-month window, status=5 conversion
    
    bars1 = ax1.bar(labels, rates, color=BAR_BLUE, width=0.6, zorder=3)
    
    x_pos = np.arange(len(labels))
    ax1.plot(x_pos, rates, color=LINE_NAVY, linewidth=2, marker='o',
             markersize=5, zorder=4)
    
    for i, (bar, rate) in enumerate(zip(bars1, rates)):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f"{rate}%", ha='center', va='bottom', fontsize=8.5,
                fontweight='bold', color=NAVY)
    
    ax1.annotate(cfg.CALL_MULTIPLIER, xy=(3, 69.8), xytext=(2.2, 85),
                fontsize=14, fontweight='bold', color=NAVY, ha='center')
    
    ax1.set_ylabel("Your Conversion Rate (%)", fontsize=8, color=GREY_TEXT)
    ax1.set_title("Your Conversion by Call Activity", fontsize=9.5,
                  fontweight='bold', color=NAVY, pad=10)
    ax1.set_ylim(0, 108)
    ax1.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax1.tick_params(axis='both', labelsize=7.5)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color('#D5D7DA')
    ax1.spines['bottom'].set_color('#D5D7DA')
    ax1.grid(axis='y', alpha=0.3, linewidth=0.5)

    # ── Chart 2: Quoted vs Unquoted ──
    labels2 = ["Unquoted\nLeads", "Quoted\nLeads"]
    rates2 = cfg.QUOTED_VS_UNQUOTED
    
    bars2 = ax2.bar(labels2, rates2, color=BAR_BLUE, width=0.5, zorder=3)
    
    ax2.plot([0, 1], rates2, color=LINE_NAVY, linewidth=2, marker='o',
             markersize=5, zorder=4)
    
    for bar, rate in zip(bars2, rates2):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                f"{rate}%", ha='center', va='bottom', fontsize=8.5,
                fontweight='bold', color=NAVY)
    
    ax2.annotate(cfg.QUOTE_MULTIPLIER, xy=(0.5, 55), xytext=(0.5, 50),
                fontsize=14, fontweight='bold', color=NAVY, ha='center')
    
    ax2.set_ylabel("Your Conversion Rate (%)", fontsize=8, color=GREY_TEXT)
    ax2.set_title("Your Conversion: Quoted vs Unquoted", fontsize=9.5,
                  fontweight='bold', color=NAVY, pad=10)
    ax2.set_ylim(0, 80)
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax2.tick_params(axis='both', labelsize=7.5)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['left'].set_color('#D5D7DA')
    ax2.spines['bottom'].set_color('#D5D7DA')
    ax2.grid(axis='y', alpha=0.3, linewidth=0.5)

    fig.suptitle("What Drives Your Results", fontsize=11, fontweight='bold',
                 color=NAVY, y=0.95)

    fig.savefig(out_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return out_path


def draw_section10(output_path):
    chart_path = output_path.replace('.pdf', '_chart.png')
    make_charts(chart_path)
    
    c = canvas.Canvas(output_path, pagesize=A4)
    
    
    # Section heading
    y = H - 28 * mm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(NAVY))
    c.drawString(ML, y, "10. What Your Data Says Works")

    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E9EAEB"))
    c.setLineWidth(0.3)
    c.line(ML, y, W - MR, y)
    
    # Subtitle
    y -= 6 * mm
    sub_style = ParagraphStyle("sub", fontName="Helvetica", fontSize=10,
                                leading=13, textColor=colors.HexColor(BODY_TEXT))
    sub = Paragraph(
        cfg.WHAT_WORKS_INTRO,
        sub_style
    )
    sw, sh = sub.wrap(UW, 40)
    sub.drawOn(c, ML, y - sh)
    y -= sh + 6 * mm
    
    # Chart
    chart_w = UW
    chart_h = chart_w * 0.48
    c.drawImage(chart_path, ML, y - chart_h, width=chart_w, height=chart_h)
    y -= chart_h + 5 * mm
    
    # ── Your Best Conversion Driver: Repeated Contact ──
    green = "#252B37"  # dark blue for highlights
    heading_style = ParagraphStyle("driverhead", fontName="Helvetica-Bold",
                                    fontSize=12, leading=15,
                                    textColor=colors.HexColor(NAVY))
    dh = Paragraph("Your Best Conversion Driver: Repeated Contact", heading_style)
    dw, dhh = dh.wrap(UW, 30)
    dh.drawOn(c, ML, y - dhh)
    y -= dhh + 5 * mm
    
    # Narrative paragraph
    narr_style = ParagraphStyle("narr", fontName="Helvetica", fontSize=10,
                                 leading=14, textColor=colors.HexColor(BODY_TEXT))
    narr = Paragraph(
        cfg.WHAT_WORKS_NARRATIVE,
        narr_style
    )
    nw, nh = narr.wrap(UW, 60)
    narr.drawOn(c, ML, y - nh)
    y -= nh + 6 * mm
    
    # Table data
    TABLE_DATA = [
        ["0 calls", "20.5%", "$844", "37"],
        ["1 call", "46.6%", "$1,243", "\u2014"],
        ["2 calls", "60.4%", "$876", "\u2014"],
        ["3+ calls", "69.8%", "$1,266", "22"],
    ]
    
    col_w = [UW * 0.22, UW * 0.22, UW * 0.28, UW * 0.28]
    hdr_h = 7.5 * mm
    row_h = 6.5 * mm
    
    # Header row
    c.setFillColor(colors.HexColor(NAVY))
    c.rect(ML, y - hdr_h, UW, hdr_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    headers = ["Call Activity", "Your Conv. Rate", "Avg Case Value", "Leads Currently Here"]
    x = ML
    for i, hdr in enumerate(headers):
        c.drawString(x + 2.5 * mm, y - hdr_h + 2.2 * mm, hdr)
        x += col_w[i]
    y -= hdr_h
    
    # Data rows
    for idx, row in enumerate(TABLE_DATA):
        bg = colors.HexColor("#F5F5F5") if idx % 2 == 1 else colors.white
        c.setFillColor(bg)
        c.rect(ML, y - row_h, UW, row_h, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#D5D7DA"))
        c.setLineWidth(0.3)
        c.line(ML, y - row_h, ML + UW, y - row_h)
        
        is_last = (idx == len(TABLE_DATA) - 1)
        c.setFont("Helvetica-Bold" if is_last else "Helvetica", 8.5)
        c.setFillColor(colors.HexColor(green) if is_last else colors.HexColor(BODY_TEXT))
        
        x = ML
        for i, val in enumerate(row):
            c.drawString(x + 2.5 * mm, y - row_h + 2 * mm, val)
            x += col_w[i]
        y -= row_h
    
    y -= 6 * mm
    
    # Closing insight
    close_style = ParagraphStyle("close", fontName="Helvetica", fontSize=10,
                                  leading=14, textColor=colors.HexColor(BODY_TEXT))
    close = Paragraph(
        "The 37 leads currently at zero calls represent the biggest shift available "
        "in your pipeline. Based on your own numbers, moving even half of those into "
        "the \u201c1 call\u201d column would more than double their expected conversion rate.",
        close_style
    )
    cw, ch = close.wrap(UW, 50)
    close.drawOn(c, ML, y - ch)
    
    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W / 2, 18 * mm, f"SLG CRM Intelligence Report  |  Page 10 of {cfg.TOTAL_PAGES}")
    
    c.save()
    os.remove(chart_path)
    return output_path


if __name__ == "__main__":
    os.makedirs("/home/claude/adviser-monthly-reports/output", exist_ok=True)
    path = draw_section10("/home/claude/adviser-monthly-reports/output/section10_sample.pdf")
    print(f"\u2705 {path} ({os.path.getsize(path) / 1024:.0f} KB)")
