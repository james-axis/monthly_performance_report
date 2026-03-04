"""
Section 11: Your Strongest Predictor + Pipeline by Engagement Level
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
GREEN = "#252B37"  # dark blue for highlights
GREY_TEXT = "#717680"
BODY_TEXT = "#535862"


def make_pipeline_chart(out_path):
    # Data: segment, leads, conv_rate, est_premium_$K
    # Est premium = leads × conv_rate × avg_quote_value_of_converted ($2,755)
    segments = cfg.PIPELINE_SEGMENTS
    
    bar_colors = ["#252B37", "#414651", "#717680", "#D5D7DA"]
    
    fig, ax = plt.subplots(figsize=(6.5, 2.8))
    
    labels = [s[0] for s in segments]
    values = [s[3] for s in segments]
    y_pos = np.arange(len(segments))
    
    bars = ax.barh(y_pos, values, height=0.55, color=bar_colors, edgecolor='none')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8, color=BODY_TEXT)
    ax.invert_yaxis()
    ax.set_xlabel("Estimated Premium Value ($K)", fontsize=8, color=GREY_TEXT)
    ax.set_title("Your Pipeline by Engagement Level", fontsize=11, fontweight='bold',
                 color=NAVY, pad=12)
    
    # Value labels
    for i, (seg_name, leads, rate, val) in enumerate(segments):
        ax.text(val + 1.5, i, f"${val}K  ({leads} leads × {rate})",
                va='center', fontsize=7.5, color=BODY_TEXT)
    
    ax.set_xlim(0, max(values) * 1.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D5D7DA')
    ax.spines['bottom'].set_color('#D5D7DA')
    ax.tick_params(axis='x', colors=GREY_TEXT, labelsize=7.5)
    ax.grid(axis='x', alpha=0.3, linewidth=0.5)
    
    fig.savefig(out_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return out_path


def draw_section11(output_path):
    c = canvas.Canvas(output_path, pagesize=A4)
    
    
    y = H - 28 * mm

    # ── Section heading ──
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(NAVY))
    c.drawString(ML, y, "11. Your Strongest Predictor")
    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E9EAEB"))
    c.setLineWidth(0.3)
    c.line(ML, y, W - MR, y)
    y -= 6 * mm

    # ── Subsection heading ──
    heading_style = ParagraphStyle("predhead", fontName="Helvetica-Bold",
                                    fontSize=12, leading=15,
                                    textColor=colors.HexColor(NAVY))
    h = Paragraph("Getting to a Quote", heading_style)
    hw, hh = h.wrap(UW, 30)
    h.drawOn(c, ML, y - hh)
    y -= hh + 4 * mm
    
    # Narrative paragraph 1
    narr_style = ParagraphStyle("narr", fontName="Helvetica", fontSize=10,
                                 leading=14, textColor=colors.HexColor(BODY_TEXT))
    
    # Data: quoted 61.2%, unquoted 9.5%, multiplier 6.4x
    p1 = Paragraph(
        "<b>Quoted leads convert at 61.2%. Unquoted leads convert at 9.5%.</b> "
        "That\u2019s a 6.4x difference. Once a client has a quote in hand, more than "
        "half of them go through to application. Getting to the quote is the hard "
        "part \u2013 and you\u2019re clearly good at it, given your volume this month.",
        narr_style
    )
    pw, ph = p1.wrap(UW, 60)
    p1.drawOn(c, ML, y - ph)
    y -= ph + 5 * mm
    
    # Narrative paragraph 2 - stale quoted leads
    # 29 stale quoted leads (6-month window), total quote value $63,758
    # Est premium = total_qv * conversion = $63,758 * 61.2% = $39,000
    stale_count = cfg.STALE_QUOTED_COUNT
    est_premium = cfg.STALE_EST_PREMIUM
    
    p2 = Paragraph(
        f"You currently have {stale_count} quoted leads where the last recorded action was more than "
        f"5 days ago. Given your 61.2% conversion rate on quoted leads, that pool alone "
        f"represents an estimated <b><font color=\"{GREEN}\">${est_premium:,.0f} in potential "
        f"premium</font></b> based on your own averages.",
        narr_style
    )
    pw2, ph2 = p2.wrap(UW, 60)
    p2.drawOn(c, ML, y - ph2)
    y -= ph2 + 10 * mm
    
    # ── Pipeline by Engagement Level chart ──
    chart_path = output_path.replace('.pdf', '_chart.png')
    make_pipeline_chart(chart_path)
    
    chart_w = UW
    chart_h = chart_w * 0.43
    c.drawImage(chart_path, ML, y - chart_h, width=chart_w, height=chart_h)
    y -= chart_h + 8 * mm
    
    # Closing italic paragraph
    italic_style = ParagraphStyle("italic_close", fontName="Helvetica-Oblique", fontSize=10,
                                   leading=14, textColor=colors.HexColor(BODY_TEXT))
    closing = Paragraph(
        "The pattern is consistent: leads you\u2019ve engaged deeply (3+ calls, quoted with "
        "follow-up) are converting at high rates and generating strong premiums. The "
        "lighter-touch segments still have value \u2013 but your data shows they respond to "
        "the same approach that\u2019s already working on your best leads.",
        italic_style
    )
    cw, ch = closing.wrap(UW, 60)
    closing.drawOn(c, ML, y - ch)
    
    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W / 2, 18 * mm, f"SLG CRM Intelligence Report  |  Page 11 of {cfg.TOTAL_PAGES}")
    
    c.save()
    os.remove(chart_path)
    return output_path


if __name__ == "__main__":
    os.makedirs("/home/claude/adviser-monthly-reports/output", exist_ok=True)
    path = draw_section11("/home/claude/adviser-monthly-reports/output/section11_sample.pdf")
    print(f"\u2705 {path} ({os.path.getsize(path) / 1024:.0f} KB)")
