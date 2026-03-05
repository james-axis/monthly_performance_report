"""
Section 12: A Note on CRM Logging + What Stands Out This Month + Milestone Banner
Final page of the adviser report.
"""
import os
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
GREEN = "#252B37"
GOLD = "#414651"
GREY_TEXT = "#717680"
BODY_TEXT = "#535862"


def draw_section12(output_path):
    c = canvas.Canvas(output_path, pagesize=A4)

    page_num = 12 - (0 if getattr(cfg, "HAS_PAGE6", True) else 1)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W / 2, 18 * mm,
                        f"SLG | Axis CRM Intelligence | Page {page_num} of {cfg.TOTAL_PAGES} | Version 1.0.0")

    y = H - 28 * mm

    # ── CRM Note ──
    style_heading = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=12,
                                    textColor=colors.HexColor(NAVY), leading=15)
    style_body = ParagraphStyle("body", fontName="Helvetica", fontSize=10,
                                 textColor=colors.HexColor(BODY_TEXT), leading=14)

    p = Paragraph("<i>A Note on CRM Logging</i>", style_heading)
    pw, ph = p.wrap(UW, 200)
    p.drawOn(c, ML, y - ph)
    y -= ph + 10

    crm_p = Paragraph(cfg.CRM_NOTE, style_body)
    pw, ph = crm_p.wrap(UW, 200)
    crm_p.drawOn(c, ML, y - ph)
    y -= ph + 12

    # ── Summary Boxes ──
    box_w = (UW - 12) / 3
    box_h = 62
    box_y = y - box_h

    boxes = [
        {"label": "UNTOUCHED LEADS", "value": str(cfg.UNTOUCHED_LEADS),
         "sub": f"Currently converting at {cfg.UNTOUCHED_CONV}", "value_color": GREEN},
        {"label": "STALE QUOTES", "value": str(cfg.STALE_QUOTES),
         "sub": f"Your quoted conv. rate: {cfg.STALE_QUOTES_CONV}", "value_color": GREEN},
        {"label": "EST. PIPELINE VALUE", "value": cfg.EST_PIPELINE_VALUE,
         "sub": "Using your own conversion rates", "value_color": GREEN},
    ]

    for i, box in enumerate(boxes):
        bx = ML + i * (box_w + 6)
        c.setFillColor(colors.HexColor("#FAFAFA"))
        c.setStrokeColor(colors.HexColor("#D5D7DA"))
        c.setLineWidth(0.5)
        c.roundRect(bx, box_y, box_w, box_h, 4, fill=1, stroke=1)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(colors.HexColor(GREY_TEXT))
        c.drawCentredString(bx + box_w / 2, box_y + box_h - 14, box["label"])
        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(colors.HexColor(box["value_color"]))
        c.drawCentredString(bx + box_w / 2, box_y + box_h - 40, box["value"])
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(colors.HexColor(GREY_TEXT))
        c.drawCentredString(bx + box_w / 2, box_y + 6, box["sub"])

    y = box_y - 14

    # ── Formula paragraph ──
    formula_p = Paragraph(cfg.FORMULA_TEXT, style_body)
    pw, ph = formula_p.wrap(UW, 200)
    formula_p.drawOn(c, ML, y - ph)
    y -= ph + 30

    # ── What Stands Out heading ──
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(NAVY))
    c.drawString(ML, y, f"12. What Stands Out This {cfg.REPORT_MONTH_NAME}")
    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E9EAEB"))
    c.setLineWidth(0.3)
    c.line(ML, y, W - MR, y)
    y -= 6 * mm

    # ── Highlights bullets (from config) ──
    bullet_style = ParagraphStyle("bullet", fontName="Helvetica", fontSize=10,
                                   textColor=colors.HexColor(BODY_TEXT), leading=14,
                                   leftIndent=18, firstLineIndent=-18)

    for highlight in cfg.HIGHLIGHTS:
        bp = Paragraph(f"★  {highlight}", bullet_style)
        bw, bh = bp.wrap(UW, 200)
        bp.drawOn(c, ML, y - bh)
        y -= bh + 6

    y -= 8

    # ── Milestone banner (conditional) ──
    if getattr(cfg, "SHOW_MILESTONE", False) and cfg.MILESTONE_TEXT:
        c.setStrokeColor(colors.HexColor(NAVY))
        c.setLineWidth(1.5)
        c.line(ML, y, W - MR, y)
        y -= 8

        c.setFont("Helvetica-Bold", 22)
        c.setFillColor(colors.HexColor(GREEN))
        c.drawCentredString(W / 2, y - 22, cfg.MILESTONE_TEXT)

        if cfg.MILESTONE_SUB:
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.HexColor(BODY_TEXT))
            c.drawCentredString(W / 2, y - 42, cfg.MILESTONE_SUB)

        y -= 52
        c.setStrokeColor(colors.HexColor(NAVY))
        c.setLineWidth(1.5)
        c.line(ML, y, W - MR, y)

    c.save()
    return output_path


# Keep alias for any legacy callers
def build_section12():
    output = os.path.join(os.path.dirname(__file__), "output", "section12_sample.pdf")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    return draw_section12(output)


if __name__ == "__main__":
    path = build_section12()
    print(f"✅ {path} ({os.path.getsize(path) / 1024:.0f} KB)")
