# import random
# import io
# import base64
# import os
# import qrcode
# from db import get_db


# def generate_job_id() -> str:
#     """Generate unique job ID like SM-15785."""
#     db = get_db()
#     while True:
#         number = random.randint(10000, 99999)
#         job_id = f"SM-{number}"
#         result = db.table("jobs").select("id").eq("job_id", job_id).execute()
#         if not result.data:
#             return job_id


# def calculate_total(paper: float, printing: float, design: float,
#                     binding: float, other: float) -> float:
#     return round(
#         (paper or 0) + (printing or 0) + (design or 0) +
#         (binding or 0) + (other or 0), 2
#     )


# def safe_float(value, default=0.0) -> float:
#     try:
#         return float(value)
#     except (TypeError, ValueError):
#         return default


# def generate_qr_base64(data: str) -> str:
#     """Return a base64 PNG string for embedding in HTML."""
#     qr = qrcode.QRCode(version=1, box_size=4, border=2)
#     qr.add_data(data)
#     qr.make(fit=True)
#     img = qr.make_image(fill_color="black", back_color="white")
#     buf = io.BytesIO()
#     img.save(buf, format="PNG")
#     buf.seek(0)
#     return base64.b64encode(buf.read()).decode("utf-8")


# def status_badge_class(status: str) -> str:
#     return {
#         "Pending":     "badge-pending",
#         "In Progress": "badge-inprogress",
#         "Completed":   "badge-completed",
#         "Delivered":   "badge-delivered",
#     }.get(status, "badge-pending")


# # ── Supabase Storage Image Upload ────────────────────────────────

# def _get_content_type(filename: str) -> str:
#     ext = filename.rsplit(".", 1)[-1].lower()
#     return {
#         "jpg":  "image/jpeg",
#         "jpeg": "image/jpeg",
#         "png":  "image/png",
#         "gif":  "image/gif",
#         "webp": "image/webp",
#     }.get(ext, "image/jpeg")


# def upload_image_to_supabase(file_bytes: bytes, filename: str) -> str:
#     """
#     Upload image to Supabase Storage bucket 'job-images'.
#     Returns the public URL string, or '' on failure.
#     """
#     try:
#         db = get_db()
#         bucket = "job-images"
#         path   = f"jobs/{filename}"
#         content_type = _get_content_type(filename)

#         db.storage.from_(bucket).upload(
#             path,
#             file_bytes,
#             {"content-type": content_type, "upsert": "true"}
#         )
#         url = db.storage.from_(bucket).get_public_url(path)
#         return url
#     except Exception as e:
#         print(f"[Image Upload Error] {e}")
#         return ""


# # ── PDF Generation ───────────────────────────────────────────────

# def generate_job_pdf(job: dict, details: dict) -> bytes:
#     """
#     Generate a full A4 job sheet PDF with grand total.
#     Returns PDF as bytes.
#     """
#     from reportlab.lib.pagesizes import A4
#     from reportlab.lib import colors
#     from reportlab.lib.units import mm
#     from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
#                                     Paragraph, Spacer, HRFlowable)
#     from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
#     from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

#     buf = io.BytesIO()
#     doc = SimpleDocTemplate(buf, pagesize=A4,
#                             topMargin=12*mm, bottomMargin=12*mm,
#                             leftMargin=12*mm, rightMargin=12*mm)

#     styles = getSampleStyleSheet()
#     W = A4[0] - 24*mm  # usable width

#     title_style = ParagraphStyle("title", parent=styles["Normal"],
#                                   fontSize=16, fontName="Helvetica-Bold",
#                                   alignment=TA_CENTER, spaceAfter=2)
#     sub_style   = ParagraphStyle("sub", parent=styles["Normal"],
#                                   fontSize=9, alignment=TA_CENTER, spaceAfter=6)

#     # ✅ NEW (address style only added)
#     address_style = ParagraphStyle("addr", parent=styles["Normal"],
#                                   fontSize=8, alignment=TA_CENTER, spaceAfter=6)

#     section_style = ParagraphStyle("sec", parent=styles["Normal"],
#                                     fontSize=9, fontName="Helvetica-Bold",
#                                     textColor=colors.white)
#     cell_label  = ParagraphStyle("lbl", parent=styles["Normal"],
#                                   fontSize=8, fontName="Helvetica-Bold")
#     cell_val    = ParagraphStyle("val", parent=styles["Normal"], fontSize=8)

#     def sec_header(text):
#         t = Table([[Paragraph(text, section_style)]], colWidths=[W])
#         t.setStyle(TableStyle([
#             ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#2c3e50")),
#             ("TOPPADDING", (0,0), (-1,-1), 4),
#             ("BOTTOMPADDING", (0,0), (-1,-1), 4),
#             ("LEFTPADDING", (0,0), (-1,-1), 6),
#         ]))
#         return t

#     def kv_table(rows, cols=4):
#         col_w = W / cols
#         data = []
#         row_cells = []
#         for i, (lbl, val) in enumerate(rows):
#             row_cells.append(Paragraph(lbl, cell_label))
#             row_cells.append(Paragraph(str(val) if val else "—", cell_val))
#             if len(row_cells) == cols * 2:
#                 data.append(row_cells)
#                 row_cells = []
#         if row_cells:
#             while len(row_cells) < cols * 2:
#                 row_cells.extend([Paragraph("", cell_label), Paragraph("", cell_val)])
#             data.append(row_cells)

#         col_widths = []
#         for _ in range(cols):
#             col_widths += [col_w * 0.38, col_w * 0.62]

#         t = Table(data, colWidths=col_widths)
#         style = [
#             ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
#             ("TOPPADDING", (0,0), (-1,-1), 3),
#             ("BOTTOMPADDING", (0,0), (-1,-1), 3),
#             ("LEFTPADDING", (0,0), (-1,-1), 4),
#             ("VALIGN", (0,0), (-1,-1), "TOP"),
#         ]
#         for c in range(0, cols*2, 2):
#             style.append(("BACKGROUND", (c,0), (c,-1), colors.HexColor("#f0f4f8")))
#         t.setStyle(TableStyle(style))
#         return t

#     def v(key, fallback=""):
#         val = details.get(key) or job.get(key) or fallback
#         if isinstance(val, bool):
#             return "Yes" if val else "No"
#         return val

#     story = []

#     story.append(Paragraph("🖨 Shree Murari Mudranalaya", title_style))

#     story.append(Paragraph(
#     "1328/13 Plot No. 2, Opp M.S.E.B Meter Testing Office,<br/>"
#     "Y.P. Power Nagar, Kolhapur – 416008<br/>"
#     "✉ abhipadwale@gmail.com",
#     sub_style))

#     story.append(Paragraph(f"Job ID: {job.get('job_id','')}  |  Status: {job.get('status','')}", sub_style))
#     story.append(HRFlowable(width=W, thickness=1, color=colors.HexColor("#2c3e50")))
#     story.append(Spacer(1, 3*mm))

#     cust = job.get("customers") or {}
#     story.append(sec_header("JOB INFORMATION"))
#     story.append(kv_table([
#         ("Job Name",        job.get("job_name","")),
#         ("Customer",        cust.get("name","")),
#         ("Mobile",          cust.get("mobile","")),
#         ("Invoice No.",     job.get("invoice_number","")),
#         ("Copies",          job.get("copies","")),
#         ("Made By",         job.get("made_by","")),
#         ("Receiving Date",  str(job.get("receiving_date",""))),
#         ("Delivery Date",   str(job.get("delivery_date",""))),
#         ("Job Info",        job.get("job_information","")),
#         ("Address",         cust.get("address","")),
#     ], cols=2))
#     story.append(Spacer(1, 3*mm))

#     story.append(sec_header("PRINTING"))
#     story.append(kv_table([
#         ("Machine",          v("machine")),
#         ("Print Size",       v("size_printing")),
#         ("Color",            v("color")),
#         ("Color Details",    v("color_details")),
#         ("Backside Print",   "Yes" if details.get("backside_printing") else "No"),
#         ("Back Color",       v("back_color")),
#         ("Total Printing",   v("total_printing")),
#         ("Total Sets",       v("total_sets")),
#     ]))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("PLATE"))
#     story.append(kv_table([
#         ("Provider",  v("plate_provider")),
#         ("Type",      v("plate_type")),
#         ("Size",      v("plate_size")),
#     ], cols=3))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("DESIGN"))
#     story.append(kv_table([
#         ("Size",    v("design_size")),
#         ("Pages",   v("design_pages")),
#         ("Details", v("design_details")),
#     ], cols=3))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("LAMINATION"))
#     story.append(kv_table([
#         ("Provider",      v("lam_provider")),
#         ("Type",          v("lam_type")),
#         ("Size",          v("lam_size")),
#         ("Quantity",      v("lam_quantity")),
#         ("Spot Qty",      v("lam_spot_quantity")),
#     ], cols=3))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("PUNCHING / CREASING / FOLDING"))
#     story.append(kv_table([
#         ("Punch Provider", v("punch_provider")),
#         ("Punch Size",     v("punch_size")),
#         ("Punch Qty",      v("punch_quantity")),
#         ("Crease Provider",v("crease_provider")),
#         ("Crease Type",    v("crease_type")),
#         ("Crease Size",    v("crease_size")),
#         ("Crease Qty",     v("crease_quantity")),
#         ("Fold Provider",  v("fold_provider")),
#         ("Fold Size",      v("fold_size")),
#         ("Fold Qty",       v("fold_quantity")),
#     ]))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("PAPER"))
#     story.append(kv_table([
#         ("Provider", v("paper_provider")),
#         ("Size",     v("paper_size")),
#         ("Sheets",   v("paper_sheets")),
#         ("Type",     v("paper_type")),
#         ("GSM",      v("paper_gsm")),
#     ], cols=3))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("BINDING"))
#     story.append(kv_table([
#         ("Provider", v("bind_provider")),
#         ("Type",     v("bind_type")),
#         ("Size",     v("bind_size")),
#         ("Pages",    v("bind_pages")),
#         ("Qty",      v("bind_quantity")),
#     ], cols=3))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("ENVELOPE"))
#     story.append(kv_table([
#         ("Provider", v("env_provider")),
#         ("Type",     v("env_type")),
#         ("Size",     v("env_size")),
#         ("Qty",      v("env_quantity")),
#     ]))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("CUTTING & OTHER INSTRUCTIONS"))
#     story.append(kv_table([
#         ("Cutting Instructions", v("cutting_instructions")),
#         ("Other Instructions",   v("other_instructions")),
#     ], cols=2))
#     story.append(Spacer(1, 3*mm))

#     story.append(sec_header("COST BREAKDOWN"))
#     paper_c    = safe_float(job.get("paper_cost", 0))
#     printing_c = safe_float(job.get("printing_cost", 0))
#     design_c   = safe_float(job.get("design_cost", 0))
#     binding_c  = safe_float(job.get("binding_cost", 0))
#     other_c    = safe_float(job.get("other_charges", 0))
#     grand_total = paper_c + printing_c + design_c + binding_c + other_c

#     cost_data = [
#         ["Cost Type", "Amount (Rs.)"],
#         ["Paper Cost",     f"Rs. {paper_c:.2f}"],
#         ["Printing Cost",  f"Rs. {printing_c:.2f}"],
#         ["Design Cost",    f"Rs. {design_c:.2f}"],
#         ["Binding Cost",   f"Rs. {binding_c:.2f}"],
#         ["Other Charges",  f"Rs. {other_c:.2f}"],
#         ["GRAND TOTAL",    f"Rs. {grand_total:.2f}"],
#     ]
#     cost_table = Table(cost_data, colWidths=[W*0.6, W*0.4])
#     cost_table.setStyle(TableStyle([
#         ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#2c3e50")),
#         ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
#         ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
#         ("FONTSIZE",     (0,0), (-1,-1), 9),
#         ("ALIGN",        (1,0), (1,-1), "RIGHT"),
#         ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
#         ("TOPPADDING",   (0,0), (-1,-1), 4),
#         ("BOTTOMPADDING",(0,0), (-1,-1), 4),
#         ("LEFTPADDING",  (0,0), (-1,-1), 6),
#         ("BACKGROUND",   (0,-1), (-1,-1), colors.HexColor("#27ae60")),
#         ("TEXTCOLOR",    (0,-1), (-1,-1), colors.white),
#         ("FONTNAME",     (0,-1), (-1,-1), "Helvetica-Bold"),
#         ("FONTSIZE",     (0,-1), (-1,-1), 11),
#     ]))
#     story.append(cost_table)
#     story.append(Spacer(1, 4*mm))

#     from datetime import datetime
#     story.append(HRFlowable(width=W, thickness=0.5, color=colors.grey))
#     footer_style = ParagraphStyle("footer", parent=styles["Normal"],
#                                    fontSize=7, textColor=colors.grey,
#                                    alignment=TA_CENTER)
#     story.append(Paragraph(
#         f"Generated on {datetime.now().strftime('%d-%m-%Y %H:%M')}  |  "
#         f"Job ID: {job.get('job_id','')}  |  Shree Murari mudranalaya",
#         footer_style))

#     doc.build(story)
#     buf.seek(0)
#     return buf.read()
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
    Premium full-page A4 job sheet PDF.
    Rich header banner + 2-column sections filling the entire page.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from datetime import datetime

    PAGE_W, PAGE_H = A4
    L_MAR = R_MAR = 12 * mm
    T_MAR = B_MAR = 10 * mm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=T_MAR, bottomMargin=B_MAR,
                            leftMargin=L_MAR, rightMargin=R_MAR)

    styles  = getSampleStyleSheet()
    W       = PAGE_W - L_MAR - R_MAR          # 186 mm usable
    COL     = (W - 4*mm) / 2                  # each half-column

    # ── Palette ───────────────────────────────────────────────────
    C_NAVY   = colors.HexColor("#0d1b2a")
    C_BLUE   = colors.HexColor("#1b4f72")
    C_STEEL  = colors.HexColor("#2e86c1")
    C_ACCENT = colors.HexColor("#f39c12")
    C_LIGHT  = colors.HexColor("#eaf4fb")
    C_LBLUE  = colors.HexColor("#d6eaf8")
    C_BORDER = colors.HexColor("#aed6f1")
    C_GREY   = colors.HexColor("#5d6d7e")
    C_WHITE  = colors.white
    C_BLACK  = colors.HexColor("#1a1a2e")

    # ── Para styles ───────────────────────────────────────────────
    def ps(name, size, bold=False, color=C_BLACK, align=TA_LEFT, leading=None):
        font = "Helvetica-Bold" if bold else "Helvetica"
        p = ParagraphStyle(name, parent=styles["Normal"],
                           fontSize=size, fontName=font,
                           textColor=color, alignment=align)
        if leading:
            p.leading = leading
        return p

    lbl_st  = ps("lbl",  7.5, bold=True,  color=C_GREY)
    val_st  = ps("val",  8.5, bold=False, color=C_BLACK)
    sec_st  = ps("sec",  8,   bold=True,  color=C_WHITE)
    foot_st = ps("ft",   7,   bold=False, color=C_GREY, align=TA_CENTER)

    def v(key, fallback="—"):
        raw = details.get(key) or job.get(key)
        if raw is None or raw == "" or raw == False:
            return fallback
        if raw is True:
            return "Yes"
        return str(raw)

    # ── Helpers ───────────────────────────────────────────────────
    def sec_header(text, width=W, color=C_BLUE):
        t = Table([[Paragraph(text, sec_st)]], colWidths=[width])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), color),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ("LINEBELOW",     (0,0), (-1,-1), 1.5, C_ACCENT),
        ]))
        return t

    def kv_table(pairs, width=W, ncols=4):
        """Render key-value pairs in ncols columns."""
        cw   = width / ncols
        lw   = cw * 0.42
        vw   = cw * 0.58
        widths = [lw, vw] * ncols

        data, row = [], []
        for lbl, val in pairs:
            row += [Paragraph(lbl, lbl_st), Paragraph(str(val), val_st)]
            if len(row) == ncols * 2:
                data.append(row); row = []
        if row:
            while len(row) < ncols * 2:
                row += [Paragraph("", lbl_st), Paragraph("", val_st)]
            data.append(row)

        ts = [
            ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 5),
            ("RIGHTPADDING",  (0,0), (-1,-1), 5),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]
        for c in range(0, ncols*2, 2):
            ts.append(("BACKGROUND", (c, 0), (c, -1), C_LBLUE))
        t = Table(data, colWidths=widths)
        t.setStyle(TableStyle(ts))
        return t

    def section(title, pairs, width=W, ncols=4, color=C_BLUE):
        return [sec_header(title, width, color), kv_table(pairs, width, ncols), Spacer(1, 2*mm)]

    def two_col_block(left_sections, right_sections):
        """Side-by-side block from lists of (title, pairs, ncols)."""
        def build_col(sec_list, w):
            elems = []
            for title, pairs, nc in sec_list:
                elems += section(title, pairs, w, nc)
            return elems

        left  = build_col(left_sections,  COL)
        right = build_col(right_sections, COL)
        t = Table([[left, right]], colWidths=[COL, COL])
        t.setStyle(TableStyle([
            ("VALIGN",       (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",  (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING",   (0,0), (-1,-1), 0),
            ("BOTTOMPADDING",(0,0), (-1,-1), 0),
            ("LEFTPADDING",  (1,0), (1,-1),  4*mm),
        ]))
        return t

    cust  = job.get("customers") or {}
    story = []

    # ══════════════════════════════════════════════════════════════
    #  HEADER
    # ══════════════════════════════════════════════════════════════
    #  Top accent bar
    accent_bar = Table([[""]], colWidths=[W], rowHeights=[3])
    accent_bar.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), C_ACCENT)]))
    story.append(accent_bar)

    # Main header: logo area left, address right
    left_header = [
        Paragraph("SHREE MURARI", ps("h1", 18, bold=True, color=C_WHITE)),
        Paragraph("MUDRANALAYA", ps("h2", 15, bold=True, color=C_ACCENT)),
        Spacer(1, 2*mm),
        Paragraph("Printing Solutions", ps("h3", 9, color=C_BORDER)),
    ]
    right_header = [
        Paragraph("1328/13, Plot No. 2, Opp M.S.E.B Meter Testing Office,",
                  ps("a1", 8, color=C_BORDER, align=TA_RIGHT)),
        Paragraph("Y.P. Power Nagar, Kolhapur – 416008",
                  ps("a2", 8, color=C_BORDER, align=TA_RIGHT)),
        Spacer(1, 2*mm),
        Paragraph("abhipadwale@gmail.com",
                  ps("a3", 8, color=C_ACCENT, align=TA_RIGHT)),
    ]

    header_main = Table(
        [[left_header, right_header]],
        colWidths=[W * 0.45, W * 0.55]
    )
    header_main.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_NAVY),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (0,-1),  10),
        ("RIGHTPADDING",  (1,0), (1,-1),  10),
    ]))
    story.append(header_main)

    # Job meta strip
    meta_text = (
        f"<b>Job ID:</b> {job.get('job_id','')}    "
        f"<b>Invoice:</b> {job.get('invoice_number','—')}    "
        f"<b>Status:</b> {job.get('status','')}    "
        f"<b>Received:</b> {job.get('receiving_date','')}    "
        f"<b>Delivery:</b> {job.get('delivery_date','—')}"
    )
    meta_strip = Table(
        [[Paragraph(meta_text, ps("meta", 8, color=C_NAVY, align=TA_CENTER))]],
        colWidths=[W]
    )
    meta_strip.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_ACCENT),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(meta_strip)
    story.append(Spacer(1, 3*mm))

    # ══════════════════════════════════════════════════════════════
    #  JOB INFORMATION  (full width, 4 cols)
    # ══════════════════════════════════════════════════════════════
    story += section("  JOB INFORMATION", [
        ("Job Name",      job.get("job_name", "—")),
        ("Customer",      cust.get("name", "—")),
        ("Mobile",        cust.get("mobile", "—")),
        ("Made By",       job.get("made_by", "—")),
        ("Copies",        str(job.get("copies", "—"))),
        ("Job Info",      job.get("job_information", "—")),
        ("Invoice No.",   job.get("invoice_number", "—")),
        ("Address",       cust.get("address", "—")),
    ], W, ncols=4, color=C_STEEL)

    # ══════════════════════════════════════════════════════════════
    #  2-COLUMN BODY
    # ══════════════════════════════════════════════════════════════
    story.append(two_col_block(
        left_sections=[
            ("  PRINTING", [
                ("Machine",       v("machine")),
                ("Print Size",    v("size_printing")),
                ("Color",         v("color")),
                ("Color Details", v("color_details")),
                ("Backside",      "Yes" if details.get("backside_printing") else "No"),
                ("Back Color",    v("back_color")),
                ("Total Printing",v("total_printing")),
                ("Total Sets",    v("total_sets")),
            ], 2),
            ("  PLATE", [
                ("Provider", v("plate_provider")),
                ("Type",     v("plate_type")),
                ("Size",     v("plate_size")),
            ], 2),
            ("  DESIGN", [
                ("Size",    v("design_size")),
                ("Pages",   v("design_pages")),
                ("Details", v("design_details")),
            ], 2),
            ("  PAPER", [
                ("Provider", v("paper_provider")),
                ("Size",     v("paper_size")),
                ("Sheets",   v("paper_sheets")),
                ("Type",     v("paper_type")),
                ("GSM",      v("paper_gsm")),
            ], 2),
        ],
        right_sections=[
            ("  LAMINATION", [
                ("Provider", v("lam_provider")),
                ("Type",     v("lam_type")),
                ("Size",     v("lam_size")),
                ("Qty",      v("lam_quantity")),
                ("Spot Qty", v("lam_spot_quantity")),
            ], 2),
            ("  PUNCHING", [
                ("Provider", v("punch_provider")),
                ("Size",     v("punch_size")),
                ("Qty",      v("punch_quantity")),
            ], 2),
            ("  CREASING", [
                ("Provider", v("crease_provider")),
                ("Type",     v("crease_type")),
                ("Size",     v("crease_size")),
                ("Qty",      v("crease_quantity")),
            ], 2),
            ("  FOLDING", [
                ("Provider", v("fold_provider")),
                ("Size",     v("fold_size")),
                ("Qty",      v("fold_quantity")),
            ], 2),
            ("  BINDING", [
                ("Provider", v("bind_provider")),
                ("Type",     v("bind_type")),
                ("Size",     v("bind_size")),
                ("Pages",    v("bind_pages")),
                ("Qty",      v("bind_quantity")),
            ], 2),
            ("  ENVELOPE", [
                ("Provider", v("env_provider")),
                ("Type",     v("env_type")),
                ("Size",     v("env_size")),
                ("Qty",      v("env_quantity")),
            ], 2),
        ]
    ))
    story.append(Spacer(1, 3*mm))

    # ══════════════════════════════════════════════════════════════
    #  CUTTING & OTHER (full width)
    # ══════════════════════════════════════════════════════════════
    story += section("  CUTTING & OTHER INSTRUCTIONS", [
        ("Cutting Instructions", v("cutting_instructions")),
        ("Other Instructions",   v("other_instructions")),
    ], W, ncols=2, color=C_STEEL)

    # ══════════════════════════════════════════════════════════════
    #  FOOTER
    # ══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 4*mm))

    bottom_bar = Table(
        [[Paragraph(
            f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}   |   "
            f"Job ID: {job.get('job_id','')}   |   Shree Murari Mudranalaya, Kolhapur",
            ps("fb", 7.5, color=C_WHITE, align=TA_CENTER)
        )]],
        colWidths=[W]
    )
    bottom_bar.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(bottom_bar)

    # bottom accent line
    story.append(Table([[""]], colWidths=[W], rowHeights=[3]))
    story[-1].setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), C_ACCENT)]))

    doc.build(story)
    buf.seek(0)
    return buf.read()
# import random
# import io
# import base64
# import os
# import qrcode
# from db import get_db


# def generate_job_id() -> str:
#     """Generate unique job ID like SM-15785."""
#     db = get_db()
#     while True:
#         number = random.randint(10000, 99999)
#         job_id = f"SM-{number}"
#         result = db.table("jobs").select("id").eq("job_id", job_id).execute()
#         if not result.data:
#             return job_id


# def calculate_total(paper: float, printing: float, design: float,
#                     binding: float, other: float) -> float:
#     return round(
#         (paper or 0) + (printing or 0) + (design or 0) +
#         (binding or 0) + (other or 0), 2
#     )


# def safe_float(value, default=0.0) -> float:
#     try:
#         return float(value)
#     except (TypeError, ValueError):
#         return default


# def generate_qr_base64(data: str) -> str:
#     """Return a base64 PNG string for embedding in HTML."""
#     qr = qrcode.QRCode(version=1, box_size=4, border=2)
#     qr.add_data(data)
#     qr.make(fit=True)
#     img = qr.make_image(fill_color="black", back_color="white")
#     buf = io.BytesIO()
#     img.save(buf, format="PNG")
#     buf.seek(0)
#     return base64.b64encode(buf.read()).decode("utf-8")


# def status_badge_class(status: str) -> str:
#     return {
#         "Pending":     "badge-pending",
#         "In Progress": "badge-inprogress",
#         "Completed":   "badge-completed",
#         "Delivered":   "badge-delivered",
#     }.get(status, "badge-pending")


# # ── Supabase Storage Image Upload ────────────────────────────────

# def _get_content_type(filename: str) -> str:
#     ext = filename.rsplit(".", 1)[-1].lower()
#     return {
#         "jpg":  "image/jpeg",
#         "jpeg": "image/jpeg",
#         "png":  "image/png",
#         "gif":  "image/gif",
#         "webp": "image/webp",
#     }.get(ext, "image/jpeg")


# def upload_image_to_supabase(file_bytes: bytes, filename: str) -> str:
#     """
#     Upload image to Supabase Storage bucket 'job-images'.
#     Returns the public URL string, or '' on failure.
#     """
#     try:
#         db = get_db()
#         bucket = "job-images"
#         path   = f"jobs/{filename}"
#         content_type = _get_content_type(filename)

#         db.storage.from_(bucket).upload(
#             path,
#             file_bytes,
#             {"content-type": content_type, "upsert": "true"}
#         )
#         url = db.storage.from_(bucket).get_public_url(path)
#         return url
#     except Exception as e:
#         print(f"[Image Upload Error] {e}")
#         return ""


# # ── PDF Generation ───────────────────────────────────────────────

# def generate_job_pdf(job: dict, details: dict) -> bytes:
#     """
#     Generate a full A4 job sheet PDF with grand total.
#     Returns PDF as bytes.
#     """
#     from reportlab.lib.pagesizes import A4
#     from reportlab.lib import colors
#     from reportlab.lib.units import mm
#     from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
#                                     Paragraph, Spacer, HRFlowable)
#     from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
#     from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

#     buf = io.BytesIO()
#     doc = SimpleDocTemplate(buf, pagesize=A4,
#                             topMargin=12*mm, bottomMargin=12*mm,
#                             leftMargin=12*mm, rightMargin=12*mm)

#     styles = getSampleStyleSheet()
#     W = A4[0] - 24*mm  # usable width

#     title_style = ParagraphStyle("title", parent=styles["Normal"],
#                                   fontSize=16, fontName="Helvetica-Bold",
#                                   alignment=TA_CENTER, spaceAfter=2)
#     sub_style   = ParagraphStyle("sub", parent=styles["Normal"],
#                                   fontSize=9, alignment=TA_CENTER, spaceAfter=6)

#     # ✅ NEW (address style only added)
#     address_style = ParagraphStyle("addr", parent=styles["Normal"],
#                                   fontSize=8, alignment=TA_CENTER, spaceAfter=6)

#     section_style = ParagraphStyle("sec", parent=styles["Normal"],
#                                     fontSize=9, fontName="Helvetica-Bold",
#                                     textColor=colors.white)
#     cell_label  = ParagraphStyle("lbl", parent=styles["Normal"],
#                                   fontSize=8, fontName="Helvetica-Bold")
#     cell_val    = ParagraphStyle("val", parent=styles["Normal"], fontSize=8)

#     def sec_header(text):
#         t = Table([[Paragraph(text, section_style)]], colWidths=[W])
#         t.setStyle(TableStyle([
#             ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#2c3e50")),
#             ("TOPPADDING", (0,0), (-1,-1), 4),
#             ("BOTTOMPADDING", (0,0), (-1,-1), 4),
#             ("LEFTPADDING", (0,0), (-1,-1), 6),
#         ]))
#         return t

#     def kv_table(rows, cols=4):
#         col_w = W / cols
#         data = []
#         row_cells = []
#         for i, (lbl, val) in enumerate(rows):
#             row_cells.append(Paragraph(lbl, cell_label))
#             row_cells.append(Paragraph(str(val) if val else "—", cell_val))
#             if len(row_cells) == cols * 2:
#                 data.append(row_cells)
#                 row_cells = []
#         if row_cells:
#             while len(row_cells) < cols * 2:
#                 row_cells.extend([Paragraph("", cell_label), Paragraph("", cell_val)])
#             data.append(row_cells)

#         col_widths = []
#         for _ in range(cols):
#             col_widths += [col_w * 0.38, col_w * 0.62]

#         t = Table(data, colWidths=col_widths)
#         style = [
#             ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
#             ("TOPPADDING", (0,0), (-1,-1), 3),
#             ("BOTTOMPADDING", (0,0), (-1,-1), 3),
#             ("LEFTPADDING", (0,0), (-1,-1), 4),
#             ("VALIGN", (0,0), (-1,-1), "TOP"),
#         ]
#         for c in range(0, cols*2, 2):
#             style.append(("BACKGROUND", (c,0), (c,-1), colors.HexColor("#f0f4f8")))
#         t.setStyle(TableStyle(style))
#         return t

#     def v(key, fallback=""):
#         val = details.get(key) or job.get(key) or fallback
#         if isinstance(val, bool):
#             return "Yes" if val else "No"
#         return val

#     story = []

#     story.append(Paragraph("🖨 Shree Murari Mudranalaya", title_style))

#     story.append(Paragraph(
#     "1328/13 Plot No. 2, Opp M.S.E.B Meter Testing Office,<br/>"
#     "Y.P. Power Nagar, Kolhapur – 416008<br/>"
#     "✉ abhipadwale@gmail.com",
#     sub_style))

#     story.append(Paragraph(f"Job ID: {job.get('job_id','')}  |  Status: {job.get('status','')}", sub_style))
#     story.append(HRFlowable(width=W, thickness=1, color=colors.HexColor("#2c3e50")))
#     story.append(Spacer(1, 3*mm))

#     cust = job.get("customers") or {}
#     story.append(sec_header("JOB INFORMATION"))
#     story.append(kv_table([
#         ("Job Name",        job.get("job_name","")),
#         ("Customer",        cust.get("name","")),
#         ("Mobile",          cust.get("mobile","")),
#         ("Invoice No.",     job.get("invoice_number","")),
#         ("Copies",          job.get("copies","")),
#         ("Made By",         job.get("made_by","")),
#         ("Receiving Date",  str(job.get("receiving_date",""))),
#         ("Delivery Date",   str(job.get("delivery_date",""))),
#         ("Job Info",        job.get("job_information","")),
#         ("Address",         cust.get("address","")),
#     ], cols=2))
#     story.append(Spacer(1, 3*mm))

#     story.append(sec_header("PRINTING"))
#     story.append(kv_table([
#         ("Machine",          v("machine")),
#         ("Print Size",       v("size_printing")),
#         ("Color",            v("color")),
#         ("Color Details",    v("color_details")),
#         ("Backside Print",   "Yes" if details.get("backside_printing") else "No"),
#         ("Back Color",       v("back_color")),
#         ("Total Printing",   v("total_printing")),
#         ("Total Sets",       v("total_sets")),
#     ]))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("PLATE"))
#     story.append(kv_table([
#         ("Provider",  v("plate_provider")),
#         ("Type",      v("plate_type")),
#         ("Size",      v("plate_size")),
#     ], cols=3))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("DESIGN"))
#     story.append(kv_table([
#         ("Size",    v("design_size")),
#         ("Pages",   v("design_pages")),
#         ("Details", v("design_details")),
#     ], cols=3))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("LAMINATION"))
#     story.append(kv_table([
#         ("Provider",      v("lam_provider")),
#         ("Type",          v("lam_type")),
#         ("Size",          v("lam_size")),
#         ("Quantity",      v("lam_quantity")),
#         ("Spot Qty",      v("lam_spot_quantity")),
#     ], cols=3))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("PUNCHING / CREASING / FOLDING"))
#     story.append(kv_table([
#         ("Punch Provider", v("punch_provider")),
#         ("Punch Size",     v("punch_size")),
#         ("Punch Qty",      v("punch_quantity")),
#         ("Crease Provider",v("crease_provider")),
#         ("Crease Type",    v("crease_type")),
#         ("Crease Size",    v("crease_size")),
#         ("Crease Qty",     v("crease_quantity")),
#         ("Fold Provider",  v("fold_provider")),
#         ("Fold Size",      v("fold_size")),
#         ("Fold Qty",       v("fold_quantity")),
#     ]))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("PAPER"))
#     story.append(kv_table([
#         ("Provider", v("paper_provider")),
#         ("Size",     v("paper_size")),
#         ("Sheets",   v("paper_sheets")),
#         ("Type",     v("paper_type")),
#         ("GSM",      v("paper_gsm")),
#     ], cols=3))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("BINDING"))
#     story.append(kv_table([
#         ("Provider", v("bind_provider")),
#         ("Type",     v("bind_type")),
#         ("Size",     v("bind_size")),
#         ("Pages",    v("bind_pages")),
#         ("Qty",      v("bind_quantity")),
#     ], cols=3))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("ENVELOPE"))
#     story.append(kv_table([
#         ("Provider", v("env_provider")),
#         ("Type",     v("env_type")),
#         ("Size",     v("env_size")),
#         ("Qty",      v("env_quantity")),
#     ]))
#     story.append(Spacer(1, 2*mm))

#     story.append(sec_header("CUTTING & OTHER INSTRUCTIONS"))
#     story.append(kv_table([
#         ("Cutting Instructions", v("cutting_instructions")),
#         ("Other Instructions",   v("other_instructions")),
#     ], cols=2))
#     story.append(Spacer(1, 3*mm))

#     story.append(sec_header("COST BREAKDOWN"))
#     paper_c    = safe_float(job.get("paper_cost", 0))
#     printing_c = safe_float(job.get("printing_cost", 0))
#     design_c   = safe_float(job.get("design_cost", 0))
#     binding_c  = safe_float(job.get("binding_cost", 0))
#     other_c    = safe_float(job.get("other_charges", 0))
#     grand_total = paper_c + printing_c + design_c + binding_c + other_c

#     cost_data = [
#         ["Cost Type", "Amount (Rs.)"],
#         ["Paper Cost",     f"Rs. {paper_c:.2f}"],
#         ["Printing Cost",  f"Rs. {printing_c:.2f}"],
#         ["Design Cost",    f"Rs. {design_c:.2f}"],
#         ["Binding Cost",   f"Rs. {binding_c:.2f}"],
#         ["Other Charges",  f"Rs. {other_c:.2f}"],
#         ["GRAND TOTAL",    f"Rs. {grand_total:.2f}"],
#     ]
#     cost_table = Table(cost_data, colWidths=[W*0.6, W*0.4])
#     cost_table.setStyle(TableStyle([
#         ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#2c3e50")),
#         ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
#         ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
#         ("FONTSIZE",     (0,0), (-1,-1), 9),
#         ("ALIGN",        (1,0), (1,-1), "RIGHT"),
#         ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
#         ("TOPPADDING",   (0,0), (-1,-1), 4),
#         ("BOTTOMPADDING",(0,0), (-1,-1), 4),
#         ("LEFTPADDING",  (0,0), (-1,-1), 6),
#         ("BACKGROUND",   (0,-1), (-1,-1), colors.HexColor("#27ae60")),
#         ("TEXTCOLOR",    (0,-1), (-1,-1), colors.white),
#         ("FONTNAME",     (0,-1), (-1,-1), "Helvetica-Bold"),
#         ("FONTSIZE",     (0,-1), (-1,-1), 11),
#     ]))
#     story.append(cost_table)
#     story.append(Spacer(1, 4*mm))

#     from datetime import datetime
#     story.append(HRFlowable(width=W, thickness=0.5, color=colors.grey))
#     footer_style = ParagraphStyle("footer", parent=styles["Normal"],
#                                    fontSize=7, textColor=colors.grey,
#                                    alignment=TA_CENTER)
#     story.append(Paragraph(
#         f"Generated on {datetime.now().strftime('%d-%m-%Y %H:%M')}  |  "
#         f"Job ID: {job.get('job_id','')}  |  Shree Murari mudranalaya",
#         footer_style))

#     doc.build(story)
#     buf.seek(0)
#     return buf.read()
