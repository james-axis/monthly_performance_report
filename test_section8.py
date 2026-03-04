"""
Section 8: In-Progress Completion Forecast
Combo bar+line chart (per-period bars + cumulative line) + narrative + forecast bullets
Data from DB: 111 completed apps Jun 2025 – Jan 2026, avg 20 days
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
BUCKETS = cfg.COMPLETION_BUCKETS
PER_PERIOD_PCT = cfg.PER_PERIOD_PCT
CUMULATIVE_PCT = cfg.CUMULATIVE_PCT
TOTAL_COMPLETED = cfg.TOTAL_COMPLETED
TOTAL_SUBMITTED = cfg.TOTAL_SUBMITTED_HIST
COMPLETION_RATE = cfg.COMPLETION_RATE
AVG_DAYS = cfg.AVG_DAYS
FEB_IN_PROGRESS = cfg.FEB_IN_PROGRESS
FEB_IP_PREMIUM = cfg.FEB_IP_PREMIUM
FEB_COMMENCED_PREM = cfg.FEB_COMMENCED_PREM
EXPECTED_COMPLETIONS = cfg.EXPECTED_COMPLETIONS
EXPECTED_PREM = cfg.EXPECTED_PREM
TOTAL_FORECAST = cfg.TOTAL_FORECAST


def build_completion_chart(output_path):
    """Combo bar (per-period %) + line (cumulative %) chart."""
    fig, ax1 = plt.subplots(figsize=(7.5, 3.6))
    
    x = np.arange(len(BUCKETS))
    bar_w = 0.5
    
    # Bars: per-period %
    bar_color = "#414651"
    bars = ax1.bar(x, PER_PERIOD_PCT, width=bar_w, color=bar_color, zorder=3,
                   alpha=0.85, label="Per period")
    
    ax1.set_ylim(0, 115)
    ax1.set_ylabel("% of Applications", fontsize=9, color=NAVY)
    ax1.set_xticks(x)
    ax1.set_xticklabels(BUCKETS, fontsize=9)
    ax1.grid(axis="y", alpha=0.15)
    ax1.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)
    
    # Bar value labels
    for i, (bar, val) in enumerate(zip(bars, PER_PERIOD_PCT)):
        if i == 0:
            # Week 1: place inside bar to avoid cumulative label overlap
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 4,
                     f"{val}%", ha="center", va="top", fontsize=8.5,
                     fontweight="bold", color="white")
        else:
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                     f"{val}%", ha="center", va="bottom", fontsize=8.5,
                     fontweight="bold", color="#414651")
    
    # Line: cumulative %
    line_color = NAVY
    ax1.plot(x, CUMULATIVE_PCT, color=line_color, linewidth=2.5, marker="o",
             markersize=7, markerfacecolor=line_color, zorder=5, label="Cumulative %")
    
    # Cumulative labels
    for i, val in enumerate(CUMULATIVE_PCT):
        if i == 0:
            offset_y = 5  # Week 1: push up to avoid bar label
            ax1.text(x[i], val + offset_y, f"{val}%", ha="center", va="bottom",
                     fontsize=8.5, fontweight="bold", color=NAVY)
        elif i == len(CUMULATIVE_PCT) - 1:
            # 100%: left of dot to avoid legend
            ax1.text(x[i] - 0.4, val + 2, f"{val}%", ha="right", va="bottom",
                     fontsize=8.5, fontweight="bold", color=NAVY)
        else:
            ax1.text(x[i], val + 4, f"{val}%", ha="center", va="bottom",
                     fontsize=8.5, fontweight="bold", color=NAVY)
    
    ax1.legend(fontsize=8, framealpha=0.9, loc="center right",
              bbox_to_anchor=(1.0, 0.7))
    
    ax1.set_title(f"Application Completion Timeline (based on {TOTAL_COMPLETED} historical apps)",
                  fontsize=11, fontweight="bold", color=NAVY, pad=12)
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def draw_section8(output_path):
    c = canvas.Canvas(output_path, pagesize=A4)
    
    
    # Section heading
    y = H - 28 * mm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(NAVY))
    c.drawString(ML, y, "8. In-Progress Completion Forecast")

    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E9EAEB"))
    c.setLineWidth(0.3)
    c.line(ML, y, W - MR, y)
    
    # Subtitle
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor(BODY_TEXT))
    c.drawString(ML, y, f"Based on your historical pattern across {TOTAL_COMPLETED} completed applications (June 2025 onward):")
    
    # Chart
    y -= 5 * mm
    chart_path = output_path.replace(".pdf", "_chart.png")
    build_completion_chart(chart_path)
    
    chart_h = 62 * mm
    c.drawImage(chart_path, ML - 2 * mm, y - chart_h, width=UW + 4 * mm, height=chart_h,
                preserveAspectRatio=True, anchor="nw")
    y -= chart_h + 6 * mm
    
    # Historical summary line (italic)
    hist_style = ParagraphStyle("hist", fontName="Helvetica-Oblique", fontSize=10,
                                 leading=13, textColor=colors.HexColor(BODY_TEXT))
    hist_text = (
        f"Historical completion rate: {COMPLETION_RATE}% "
        f"({TOTAL_COMPLETED} of {TOTAL_SUBMITTED} submitted). "
        f"Average time to completion: {AVG_DAYS} days."
    )
    hist = Paragraph(hist_text, hist_style)
    hw, hh = hist.wrap(UW, 30)
    hist.drawOn(c, ML, y - hh)
    y -= hh + 10 * mm
    
    # ── Forecast section ──
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor(NAVY))
    c.drawString(ML, y, f"Applied to February's {FEB_IN_PROGRESS} in-progress apps (${FEB_IP_PREMIUM:,}):")
    y -= 10 * mm
    
    # Bullet points
    bullets = [
        f"Expected completions: ~{EXPECTED_COMPLETIONS} of {FEB_IN_PROGRESS}",
        f"Expected paid premium: ~${EXPECTED_PREM:,}",
        "Most within 3–4 weeks, larger/complex cases 4–8 weeks",
        f"Combined with ${FEB_COMMENCED_PREM:,} commenced: <b>${TOTAL_FORECAST // 1000}K+ total paid premium from February's work</b>",
    ]
    
    bullet_style = ParagraphStyle("bullet", fontName="Helvetica", fontSize=10,
                                   leading=14, textColor=colors.HexColor(BODY_TEXT),
                                   leftIndent=12, bulletIndent=0)
    
    for b in bullets:
        bp = Paragraph(f"• {b}", bullet_style)
        bw, bh = bp.wrap(UW - 10 * mm, 30)
        bp.drawOn(c, ML, y - bh)
        y -= bh + 3 * mm
    
    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W / 2, 18 * mm, f"SLG CRM Intelligence Report  |  Page 8 of {cfg.TOTAL_PAGES}")
    
    c.save()
    if os.path.exists(chart_path):
        os.remove(chart_path)
    return output_path


if __name__ == "__main__":
    os.makedirs("/home/claude/adviser-monthly-reports/output", exist_ok=True)
    path = draw_section8("/home/claude/adviser-monthly-reports/output/section8_sample.pdf")
    print(f"✅ {path} ({os.path.getsize(path) / 1024:.0f} KB)")
