"""
Section 7: Speed-to-Contact Conversion Analysis
Dual bar chart (Conversion by Call Activity | Case Value by Call Activity) + narrative
Data from Sonny's reference - to be validated against DB when reconnected
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

# Data from config
CALL_BUCKETS = cfg.CALL_BUCKETS
CONV_RATES = cfg.CONV_RATES
AVG_CASE_VALUES = cfg.AVG_CASE_VALUES
TOTAL_LEADS = cfg.TOTAL_LEADS_STC
PERIOD = cfg.STC_PERIOD

# Quoted vs unquoted insight (from DB)
QUOTED_CONV = 60.8
UNQUOTED_CONV = 7.0

# Bar colors
CONV_COLORS = ["#D5D7DA", "#717680", "#414651", "#252B37"]
CASE_COLORS = ["#A4A7AE", "#717680", "#414651", "#252B37"]


def build_speed_chart(output_path):
    """Side-by-side bar charts: Conversion Rate | Avg Case Value"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 3.8))
    fig.subplots_adjust(wspace=0.35)
    
    x = np.arange(len(CALL_BUCKETS))
    bar_w = 0.55
    
    # ── Left: Conversion by Call Activity ──
    bars1 = ax1.bar(x, CONV_RATES, width=bar_w, color=CONV_COLORS, zorder=3, edgecolor="white", linewidth=0.5)
    ax1.set_ylim(0, 105)
    ax1.set_xticks(x)
    ax1.set_xticklabels(CALL_BUCKETS, fontsize=9)
    ax1.set_ylabel("Conversion Rate (%)", fontsize=9)
    ax1.set_title("Conversion by Call Activity", fontsize=11, fontweight="bold", color=NAVY, pad=10)
    ax1.grid(axis="y", alpha=0.15)
    ax1.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)
    
    for bar, val in zip(bars1, CONV_RATES):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                 f"{val}%", ha="center", va="bottom", fontsize=9, fontweight="bold", color=NAVY)
    
    # ── Right: Avg Case Value by Call Activity ──
    bars2 = ax2.bar(x, AVG_CASE_VALUES, width=bar_w, color=CASE_COLORS, zorder=3, edgecolor="white", linewidth=0.5)
    ax2.set_ylim(0, max(AVG_CASE_VALUES) * 1.2)
    ax2.set_xticks(x)
    ax2.set_xticklabels(CALL_BUCKETS, fontsize=9)
    ax2.set_ylabel("Avg Case Value ($)", fontsize=9)
    ax2.set_title("Case Value by Call Activity", fontsize=11, fontweight="bold", color=NAVY, pad=10)
    ax2.grid(axis="y", alpha=0.15)
    ax2.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax2.spines[spine].set_visible(False)
    
    for bar, val in zip(bars2, AVG_CASE_VALUES):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 15,
                 f"${val:,}", ha="center", va="bottom", fontsize=9, fontweight="bold", color=NAVY)
    
    fig.suptitle(f"Speed-to-Contact Analysis ({TOTAL_LEADS} leads, {PERIOD})",
                 fontsize=12, fontweight="bold", color=NAVY, y=1.0)
    
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def draw_section7(output_path):
    c = canvas.Canvas(output_path, pagesize=A4)
    
    
    # Section heading
    y = H - 28 * mm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(NAVY))
    c.drawString(ML, y, "7. Speed-to-Contact Conversion Analysis")

    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E9EAEB"))
    c.setLineWidth(0.3)
    c.line(ML, y, W - MR, y)
    
    # Subtitle
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor(BODY_TEXT))
    c.drawString(ML, y, f"Conversion data from the last {PERIOD} ({TOTAL_LEADS} leads) broken down by call activity:")
    
    # Chart
    y -= 5 * mm
    chart_path = output_path.replace(".pdf", "_chart.png")
    build_speed_chart(chart_path)
    
    chart_h = 68 * mm
    c.drawImage(chart_path, ML - 5 * mm, y - chart_h, width=UW + 10 * mm, height=chart_h,
                preserveAspectRatio=True, anchor="nw")
    y -= chart_h + 8 * mm
    
    # ── Narrative ──
    narr_style = ParagraphStyle("narr", fontName="Helvetica", fontSize=10,
                                 leading=14, textColor=colors.HexColor(BODY_TEXT))
    narr_text = (
        "<b>Each additional call attempt roughly doubles the conversion rate.</b> "
        "Leads that reach the quote stage convert at 60.8% vs 7.0% for unquoted. "
        "Getting to a quote is the single strongest predictor of conversion."
    )
    narr = Paragraph(narr_text, narr_style)
    pw, ph = narr.wrap(UW, 60)
    narr.drawOn(c, ML, y - ph)
    
    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W / 2, 18 * mm, f"SLG CRM Intelligence Report  |  Page 7 of {cfg.TOTAL_PAGES}")
    
    c.save()
    if os.path.exists(chart_path):
        os.remove(chart_path)
    return output_path


if __name__ == "__main__":
    os.makedirs("/home/claude/adviser-monthly-reports/output", exist_ok=True)
    path = draw_section7("/home/claude/adviser-monthly-reports/output/section7_sample.pdf")
    print(f"✅ {path} ({os.path.getsize(path) / 1024:.0f} KB)")
