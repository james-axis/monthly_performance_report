"""
Section 12: A Note on CRM Logging + What Stands Out This Month + Milestone Banner
Final page of the adviser report.
"""
import os
import matplotlib
matplotlib.use("Agg")
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
GREEN = "#252B37"  # dark blue for value highlights
GOLD = "#414651"   # blue accent
GREY_TEXT = "#717680"
BODY_TEXT = "#535862"


def draw_header(c, page_num=12):
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W/2, 18*mm, f"SLG CRM Intelligence Report  |  Page {page_num} of {cfg.TOTAL_PAGES}")


def draw_crm_note(c, y):
    style_heading = ParagraphStyle(
        "heading", fontName="Helvetica-Bold", fontSize=12,
        textColor=colors.HexColor(NAVY), leading=15)
    style_body = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=10,
        textColor=colors.HexColor(BODY_TEXT), leading=14)

    p = Paragraph("<i>A Note on CRM Logging</i>", style_heading)
    pw, ph = p.wrap(UW, 200)
    p.drawOn(c, ML, y - ph)
    y -= ph + 10

    text = (
        "There are 45 scheduled appointments in your CRM that haven't been updated in over 7 days. "
        "It's worth noting because it affects the accuracy of reports like this one – if appointments "
        "went well and outcomes weren't logged, your true pipeline is stronger than the data shows. "
        "Either way, keeping the CRM current means these reports reflect reality and can be more "
        "useful to you."
    )
    p = Paragraph(text, style_body)
    pw, ph = p.wrap(UW, 200)
    p.drawOn(c, ML, y - ph)
    y -= ph + 12
    return y


def draw_summary_boxes(c, y):
    box_w = (UW - 12) / 3
    box_h = 62
    box_y = y - box_h

    boxes = [
        {"label": "UNTOUCHED LEADS", "value": str(cfg.UNTOUCHED_LEADS), "sub": f"Currently converting at {cfg.UNTOUCHED_CONV}",
         "value_color": GREEN},
        {"label": "STALE QUOTES", "value": str(cfg.STALE_QUOTES), "sub": f"Your quoted conv. rate: {cfg.STALE_QUOTES_CONV}",
         "value_color": GREEN},
        {"label": "EST. PIPELINE VALUE", "value": cfg.EST_PIPELINE_VALUE, "sub": "Using your own conversion rates",
         "value_color": GREEN},
    ]

    for i, box in enumerate(boxes):
        bx = ML + i * (box_w + 6)
        c.setFillColor(colors.HexColor("#FAFAFA"))
        c.setStrokeColor(colors.HexColor("#D5D7DA"))
        c.setLineWidth(0.5)
        c.roundRect(bx, box_y, box_w, box_h, 4, fill=1, stroke=1)

        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(colors.HexColor(GREY_TEXT))
        c.drawCentredString(bx + box_w/2, box_y + box_h - 14, box["label"])

        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(colors.HexColor(box["value_color"]))
        c.drawCentredString(bx + box_w/2, box_y + box_h - 40, box["value"])

        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(colors.HexColor(GREY_TEXT))
        c.drawCentredString(bx + box_w/2, box_y + 6, box["sub"])

    return box_y - 14


def draw_formula_paragraph(c, y):
    style = ParagraphStyle(
        "formula", fontName="Helvetica", fontSize=10,
        textColor=colors.HexColor(BODY_TEXT), leading=14)
    text = (
        "The formula that's driven your best month is clear: "
        "<b>repeated contact, getting to a quote quickly, and comprehensive product bundles.</b> "
        "The data suggests the biggest opportunity from here is applying that same formula to the "
        "leads already in your pipeline."
    )
    p = Paragraph(text, style)
    pw, ph = p.wrap(UW, 200)
    p.drawOn(c, ML, y - ph)
    return y - ph - 30


def draw_what_stands_out(c, y):
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(NAVY))
    c.drawString(ML, y, "12. What Stands Out This Month")

    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E9EAEB"))
    c.setLineWidth(0.3)
    c.line(ML, y, W - MR, y)
    y -= 6 * mm

    style_bullet = ParagraphStyle(
        "bullet", fontName="Helvetica", fontSize=10,
        textColor=colors.HexColor(BODY_TEXT), leading=14,
        leftIndent=18, firstLineIndent=-18)

    bullets = [
        ("First $100K month",
         " – a personal milestone and a strong result by any measure across the network."),
        ("Volume and quality simultaneously",
         " – 28 apps is the highest count and the premium average ($3,604) is also the highest. "
         "One isn't diluting the other."),
        ("Household pairs",
         " – Kolac, Vanderent, Faniyi, Rautenbach, Dornbusch, Cootee, Polgreen/Clark. "
         "Consistently converting both partners doubles revenue per referral."),
        ("8-insurer diversification",
         " – Acenda, TAL, Zurich, Encompass, MetLife, ClearView, Futura, and OnePath. "
         "No concentration risk."),
        ("Newhaven pipeline",
         " – continues to be the highest-volume, highest-converting referral source "
         "by a wide margin."),
    ]

    for label, desc in bullets:
        text = f"★ <b>{label}</b>{desc}"
        p = Paragraph(text, style_bullet)
        pw, ph = p.wrap(UW, 200)
        p.drawOn(c, ML, y - ph)
        y -= ph + 6

    return y - 8


def draw_milestone_banner(c, y):
    c.setStrokeColor(colors.HexColor(NAVY))
    c.setLineWidth(1.5)
    c.line(ML, y, W - MR, y)
    y -= 8

    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.HexColor(GREEN))
    c.drawCentredString(W/2, y - 22, "$100K MILESTONE – ACHIEVED.")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor(BODY_TEXT))
    c.drawCentredString(W/2, y - 42,
                        cfg.MILESTONE_SUB)

    y -= 52
    c.setStrokeColor(colors.HexColor(NAVY))
    c.setLineWidth(1.5)
    c.line(ML, y, W - MR, y)

    return y - 10


def build_section12():
    output = "/home/claude/adviser-monthly-reports/output/section12_sample.pdf"
    os.makedirs(os.path.dirname(output), exist_ok=True)

    c = canvas.Canvas(output, pagesize=A4)
    draw_header(c, page_num=12)

    y = H - 28 * mm

    y = draw_crm_note(c, y)
    y = draw_summary_boxes(c, y)
    y = draw_formula_paragraph(c, y)
    y = draw_what_stands_out(c, y)
    y = draw_milestone_banner(c, y)

    c.showPage()
    c.save()

    size = os.path.getsize(output)
    print(f"✅ {output} ({size/1024:.0f} KB)")
    return output


if __name__ == "__main__":
    build_section12()
