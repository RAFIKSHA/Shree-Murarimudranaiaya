import random
import io
import base64
import os
import qrcode
from db import get_db


def generate_job_id() -> str:
    """Generate unique job ID like SM-15785."""
    db = get_db()
    while True:
        number = random.randint(10000, 99999)
        job_id = f"SM-{number}"
        result = db.table("jobs").select("id").eq("job_id", job_id).execute()
        if not result.data:
            return job_id


def calculate_total(paper: float, printing: float, design: float,
                    binding: float, other: float) -> float:
    return round(
        (paper or 0) + (printing or 0) + (design or 0) +
        (binding or 0) + (other or 0), 2
    )


def safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def generate_qr_base64(data: str) -> str:
    """Return a base64 PNG string for embedding in HTML."""
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def status_badge_class(status: str) -> str:
    return {
        "Pending":     "badge-pending",
        "In Progress": "badge-inprogress",
        "Completed":   "badge-completed",
        "Delivered":   "badge-delivered",
    }.get(status, "badge-pending")


# ── Supabase Storage Image Upload ────────────────────────────────

def _get_content_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "png":  "image/png",
        "gif":  "image/gif",
        "webp": "image/webp",
    }.get(ext, "image/jpeg")


def upload_image_to_supabase(file_bytes: bytes, filename: str) -> str:
    """
    Upload image to Supabase Storage bucket 'job-images'.
    Returns the public URL string, or '' on failure.
    """
    try:
        db = get_db()
        bucket = "job-images"
        path   = f"jobs/{filename}"
        content_type = _get_content_type(filename)

        db.storage.from_(bucket).upload(
            path,
            file_bytes,
            {"content-type": content_type, "upsert": "true"}
        )
        url = db.storage.from_(bucket).get_public_url(path)
        return url
    except Exception as e:
        print(f"[Image Upload Error] {e}")
        return ""


# ── PDF Generation ───────────────────────────────────────────────

def generate_job_pdf(job: dict, details: dict) -> bytes:
    """
    Generate a full A4 job sheet PDF with grand total.
    Returns PDF as bytes.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=12*mm, bottomMargin=12*mm,
                            leftMargin=12*mm, rightMargin=12*mm)

    styles = getSampleStyleSheet()
    W = A4[0] - 24*mm  # usable width

    title_style = ParagraphStyle("title", parent=styles["Normal"],
                                  fontSize=16, fontName="Helvetica-Bold",
                                  alignment=TA_CENTER, spaceAfter=2)
    sub_style   = ParagraphStyle("sub", parent=styles["Normal"],
                                  fontSize=9, alignment=TA_CENTER, spaceAfter=6)

    # ✅ NEW (address style only added)
    address_style = ParagraphStyle("addr", parent=styles["Normal"],
                                  fontSize=8, alignment=TA_CENTER, spaceAfter=6)

    section_style = ParagraphStyle("sec", parent=styles["Normal"],
                                    fontSize=9, fontName="Helvetica-Bold",
                                    textColor=colors.white)
    cell_label  = ParagraphStyle("lbl", parent=styles["Normal"],
                                  fontSize=8, fontName="Helvetica-Bold")
    cell_val    = ParagraphStyle("val", parent=styles["Normal"], fontSize=8)

    def sec_header(text):
        t = Table([[Paragraph(text, section_style)]], colWidths=[W])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#2c3e50")),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
        ]))
        return t

    def kv_table(rows, cols=4):
        col_w = W / cols
        data = []
        row_cells = []
        for i, (lbl, val) in enumerate(rows):
            row_cells.append(Paragraph(lbl, cell_label))
            row_cells.append(Paragraph(str(val) if val else "—", cell_val))
            if len(row_cells) == cols * 2:
                data.append(row_cells)
                row_cells = []
        if row_cells:
            while len(row_cells) < cols * 2:
                row_cells.extend([Paragraph("", cell_label), Paragraph("", cell_val)])
            data.append(row_cells)

        col_widths = []
        for _ in range(cols):
            col_widths += [col_w * 0.38, col_w * 0.62]

        t = Table(data, colWidths=col_widths)
        style = [
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]
        for c in range(0, cols*2, 2):
            style.append(("BACKGROUND", (c,0), (c,-1), colors.HexColor("#f0f4f8")))
        t.setStyle(TableStyle(style))
        return t

    def v(key, fallback=""):
        val = details.get(key) or job.get(key) or fallback
        if isinstance(val, bool):
            return "Yes" if val else "No"
        return val

    story = []

    story.append(Paragraph("🖨 Shree Murari Mudranalaya", title_style))

    story.append(Paragraph(
    "1328/13 Plot No. 2, Opp M.S.E.B Meter Testing Office,<br/>"
    "Y.P. Power Nagar, Kolhapur – 416008<br/>"
    "✉ abhipadwale@gmail.com",
    sub_style))

    story.append(Paragraph(f"Job ID: {job.get('job_id','')}  |  Status: {job.get('status','')}", sub_style))
    story.append(HRFlowable(width=W, thickness=1, color=colors.HexColor("#2c3e50")))
    story.append(Spacer(1, 3*mm))

    cust = job.get("customers") or {}
    story.append(sec_header("JOB INFORMATION"))
    story.append(kv_table([
        ("Job Name",        job.get("job_name","")),
        ("Customer",        cust.get("name","")),
        ("Mobile",          cust.get("mobile","")),
        ("Invoice No.",     job.get("invoice_number","")),
        ("Copies",          job.get("copies","")),
        ("Made By",         job.get("made_by","")),
        ("Receiving Date",  str(job.get("receiving_date",""))),
        ("Delivery Date",   str(job.get("delivery_date",""))),
        ("Job Info",        job.get("job_information","")),
        ("Address",         cust.get("address","")),
    ], cols=2))
    story.append(Spacer(1, 3*mm))

    story.append(sec_header("PRINTING"))
    story.append(kv_table([
        ("Machine",          v("machine")),
        ("Print Size",       v("size_printing")),
        ("Color",            v("color")),
        ("Color Details",    v("color_details")),
        ("Backside Print",   "Yes" if details.get("backside_printing") else "No"),
        ("Back Color",       v("back_color")),
        ("Total Printing",   v("total_printing")),
        ("Total Sets",       v("total_sets")),
    ]))
    story.append(Spacer(1, 2*mm))

    story.append(sec_header("PLATE"))
    story.append(kv_table([
        ("Provider",  v("plate_provider")),
        ("Type",      v("plate_type")),
        ("Size",      v("plate_size")),
    ], cols=3))
    story.append(Spacer(1, 2*mm))

    story.append(sec_header("DESIGN"))
    story.append(kv_table([
        ("Size",    v("design_size")),
        ("Pages",   v("design_pages")),
        ("Details", v("design_details")),
    ], cols=3))
    story.append(Spacer(1, 2*mm))

    story.append(sec_header("LAMINATION"))
    story.append(kv_table([
        ("Provider",      v("lam_provider")),
        ("Type",          v("lam_type")),
        ("Size",          v("lam_size")),
        ("Quantity",      v("lam_quantity")),
        ("Spot Qty",      v("lam_spot_quantity")),
    ], cols=3))
    story.append(Spacer(1, 2*mm))

    story.append(sec_header("PUNCHING / CREASING / FOLDING"))
    story.append(kv_table([
        ("Punch Provider", v("punch_provider")),
        ("Punch Size",     v("punch_size")),
        ("Punch Qty",      v("punch_quantity")),
        ("Crease Provider",v("crease_provider")),
        ("Crease Type",    v("crease_type")),
        ("Crease Size",    v("crease_size")),
        ("Crease Qty",     v("crease_quantity")),
        ("Fold Provider",  v("fold_provider")),
        ("Fold Size",      v("fold_size")),
        ("Fold Qty",       v("fold_quantity")),
    ]))
    story.append(Spacer(1, 2*mm))

    story.append(sec_header("PAPER"))
    story.append(kv_table([
        ("Provider", v("paper_provider")),
        ("Size",     v("paper_size")),
        ("Sheets",   v("paper_sheets")),
        ("Type",     v("paper_type")),
        ("GSM",      v("paper_gsm")),
    ], cols=3))
    story.append(Spacer(1, 2*mm))

    story.append(sec_header("BINDING"))
    story.append(kv_table([
        ("Provider", v("bind_provider")),
        ("Type",     v("bind_type")),
        ("Size",     v("bind_size")),
        ("Pages",    v("bind_pages")),
        ("Qty",      v("bind_quantity")),
    ], cols=3))
    story.append(Spacer(1, 2*mm))

    story.append(sec_header("ENVELOPE"))
    story.append(kv_table([
        ("Provider", v("env_provider")),
        ("Type",     v("env_type")),
        ("Size",     v("env_size")),
        ("Qty",      v("env_quantity")),
    ]))
    story.append(Spacer(1, 2*mm))

    story.append(sec_header("CUTTING & OTHER INSTRUCTIONS"))
    story.append(kv_table([
        ("Cutting Instructions", v("cutting_instructions")),
        ("Other Instructions",   v("other_instructions")),
    ], cols=2))
    story.append(Spacer(1, 3*mm))

    story.append(sec_header("COST BREAKDOWN"))
    paper_c    = safe_float(job.get("paper_cost", 0))
    printing_c = safe_float(job.get("printing_cost", 0))
    design_c   = safe_float(job.get("design_cost", 0))
    binding_c  = safe_float(job.get("binding_cost", 0))
    other_c    = safe_float(job.get("other_charges", 0))
    grand_total = paper_c + printing_c + design_c + binding_c + other_c

    cost_data = [
        ["Cost Type", "Amount (Rs.)"],
        ["Paper Cost",     f"Rs. {paper_c:.2f}"],
        ["Printing Cost",  f"Rs. {printing_c:.2f}"],
        ["Design Cost",    f"Rs. {design_c:.2f}"],
        ["Binding Cost",   f"Rs. {binding_c:.2f}"],
        ["Other Charges",  f"Rs. {other_c:.2f}"],
        ["GRAND TOTAL",    f"Rs. {grand_total:.2f}"],
    ]
    cost_table = Table(cost_data, colWidths=[W*0.6, W*0.4])
    cost_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("ALIGN",        (1,0), (1,-1), "RIGHT"),
        ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("BACKGROUND",   (0,-1), (-1,-1), colors.HexColor("#27ae60")),
        ("TEXTCOLOR",    (0,-1), (-1,-1), colors.white),
        ("FONTNAME",     (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,-1), (-1,-1), 11),
    ]))
    story.append(cost_table)
    story.append(Spacer(1, 4*mm))

    from datetime import datetime
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.grey))
    footer_style = ParagraphStyle("footer", parent=styles["Normal"],
                                   fontSize=7, textColor=colors.grey,
                                   alignment=TA_CENTER)
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d-%m-%Y %H:%M')}  |  "
        f"Job ID: {job.get('job_id','')}  |  Shree Murari mudranalaya",
        footer_style))

    doc.build(story)
    buf.seek(0)
    return buf.read()
