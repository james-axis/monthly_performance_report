"""
Section 9: Remaining Quoted Pipeline
Quoted leads (status=3) with no application yet, ordered by quote_value DESC
Table: Client | Quoted | Referral Partner | Status
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
GREY_TEXT = "#717680"
BODY_TEXT = "#535862"
ALT_ROW = "#F5F5F5"

PIPELINE = cfg.PIPELINE
TOTAL_PIPELINE = sum(p["quoted"] for p in PIPELINE if isinstance(p["quoted"], (int, float)))

# Columns: Client (25%), Quoted (12%), Referral Partner (33%), Status (30%)
COL_W = [UW * 0.25, UW * 0.12, UW * 0.33, UW * 0.30]
ROW_H = 7 * mm
HDR_H = 8 * mm


def draw_table_header(c, y):
    """Draw navy header row."""
    c.setFillColor(colors.HexColor(NAVY))
    c.rect(ML, y - HDR_H, UW, HDR_H, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    headers = ["Client", "Quoted", "Referral Partner", "Status"]
    x = ML
    for i, hdr in enumerate(headers):
        c.drawString(x + 3 * mm, y - HDR_H + 2.5 * mm, hdr)
        x += COL_W[i]
    return y - HDR_H


def draw_table_row(c, y, row, idx):
    """Draw a single data row."""
    bg = colors.HexColor(ALT_ROW) if idx % 2 == 1 else colors.white
    c.setFillColor(bg)
    c.rect(ML, y - ROW_H, UW, ROW_H, fill=1, stroke=0)
    
    # Light border
    c.setStrokeColor(colors.HexColor("#D5D7DA"))
    c.setLineWidth(0.3)
    c.line(ML, y - ROW_H, ML + UW, y - ROW_H)
    
    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.HexColor(BODY_TEXT))
    x = ML
    
    vals = [
        row["client"],
        f"${row['quoted']:,}" if row["quoted"] else "—",
        row["source"],
        row["status"],
    ]
    for i, val in enumerate(vals):
        c.drawString(x + 3 * mm, y - ROW_H + 2.2 * mm, val)
        x += COL_W[i]
    
    return y - ROW_H


def draw_section9(output_path):
    c = canvas.Canvas(output_path, pagesize=A4)
    
    # ── PAGE 1 ──
    
    # Section heading
    y = H - 28 * mm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(NAVY))
    c.drawString(ML, y, "9. Remaining Quoted Pipeline")

    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E9EAEB"))
    c.setLineWidth(0.3)
    c.line(ML, y, W - MR, y)
    
    # Subtitle
    y -= 6 * mm
    sub_style = ParagraphStyle("sub", fontName="Helvetica", fontSize=10,
                                leading=13, textColor=colors.HexColor(BODY_TEXT))
    sub = Paragraph(
        f"Quoted leads with no application yet – these represent additional upside "
        f"beyond the ${cfg.KPI_TOTAL_SUBMITTED_RAW:,} already submitted in {cfg.REPORT_MONTH_NAME}.",
        sub_style
    )
    sw, sh = sub.wrap(UW, 40)
    sub.drawOn(c, ML, y - sh)
    y -= sh + 8 * mm
    
    if not PIPELINE:
        no_data_style = ParagraphStyle("nd", fontName="Helvetica-Oblique", fontSize=10,
                                        leading=14, textColor=colors.HexColor(BODY_TEXT))
        nd = Paragraph("No quoted leads without an application found in the CRM.", no_data_style)
        nw, nh = nd.wrap(UW, 30)
        nd.drawOn(c, ML, y - nh)
    else:
        # Table
        y = draw_table_header(c, y)

        for idx, row in enumerate(PIPELINE):
            y = draw_table_row(c, y, row, idx)

        # Total line
        y -= 8 * mm
        import calendar as _cal
        next_month_name = _cal.month_name[(cfg.REPORT_MONTH % 12) + 1]
        total_style = ParagraphStyle("total", fontName="Helvetica", fontSize=10,
                                      leading=14, textColor=colors.HexColor(BODY_TEXT))
        if TOTAL_PIPELINE > 0:
            total_text = (
                f"<b>Total pipeline value ({len(PIPELINE)} leads): ${TOTAL_PIPELINE:,}.</b> "
                f"Converting even 2–3 of these in {next_month_name} sets up another strong month."
            )
        else:
            total_text = (
                f"<b>{len(PIPELINE)} leads in quoted status</b> – quote values not yet entered in CRM. "
                "Enter quote amounts to unlock pipeline value tracking."
            )
        tp = Paragraph(total_text, total_style)
        tw, th = tp.wrap(UW, 40)
        tp.drawOn(c, ML, y - th)
    
    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(GREY_TEXT))
    c.drawCentredString(W / 2, 18 * mm, f"SLG | Axis CRM Intelligence | Page {9 - (0 if getattr(cfg, 'HAS_PAGE6', True) else 1)} of {cfg.TOTAL_PAGES} | Version 1.0.0")
    
    c.save()
    return output_path


if __name__ == "__main__":
    os.makedirs("/home/claude/adviser-monthly-reports/output", exist_ok=True)
    path = draw_section9("/home/claude/adviser-monthly-reports/output/section9_sample.pdf")
    print(f"✅ {path} ({os.path.getsize(path) / 1024:.0f} KB)")
