from db import get_db
from utils import generate_job_id, safe_float


# ══════════════════════════════════════════
#  CUSTOMER OPERATIONS
# ══════════════════════════════════════════

def get_all_customers():
    db = get_db()
    return db.table("customers").select("*").order("created_at", desc=True).execute().data


def get_customer(customer_id: int):
    db = get_db()
    result = db.table("customers").select("*").eq("id", customer_id).single().execute()
    return result.data


def search_customers(query: str):
    db = get_db()
    return db.table("customers").select("*").ilike("name", f"%{query}%").execute().data


def create_customer(name: str, mobile: str, address: str = ""):
    db = get_db()
    return db.table("customers").insert({
        "name": name, "mobile": mobile, "address": address
    }).execute().data


def update_customer(customer_id: int, name: str, mobile: str, address: str = ""):
    db = get_db()
    return db.table("customers").update({
        "name": name, "mobile": mobile, "address": address
    }).eq("id", customer_id).execute().data


def delete_customer(customer_id: int):
    db = get_db()
    db.table("customers").delete().eq("id", customer_id).execute()


def get_customer_jobs(customer_id: int):
    db = get_db()
    return db.table("jobs").select("*").eq("customer_id", customer_id)\
             .order("created_at", desc=True).execute().data


# ══════════════════════════════════════════
#  JOB OPERATIONS
# ══════════════════════════════════════════

def get_all_jobs(status_filter: str = None):
    db = get_db()
    q = db.table("jobs").select(
        "*, customers(name, mobile)"
    ).order("created_at", desc=True)
    if status_filter:
        q = q.eq("status", status_filter)
    return q.execute().data


def get_job(job_pk: int):
    db = get_db()
    return db.table("jobs").select(
        "*, customers(name, mobile, address)"
    ).eq("id", job_pk).single().execute().data


def get_job_details(job_pk: int):
    db = get_db()
    result = db.table("job_details").select("*").eq("job_id", job_pk).execute()
    return result.data[0] if result.data else {}


def _build_job_row(form: dict) -> dict:
    """Build job row dict with explicit total_cost calculation."""
    paper    = safe_float(form.get("paper_cost"))
    printing = safe_float(form.get("printing_cost"))
    design   = safe_float(form.get("design_cost"))
    binding  = safe_float(form.get("binding_cost"))
    other    = safe_float(form.get("other_charges"))
    total    = round(paper + printing + design + binding + other, 2)

    return {
        "customer_id":     int(form["customer_id"]) if form.get("customer_id") else None,
        "job_name":        form.get("job_name", ""),
        "copies":          int(form.get("copies", 1) or 1),
        "invoice_number":  form.get("invoice_number", ""),
        "made_by":         form.get("made_by", ""),
        "job_information": form.get("job_information", ""),
        "status":          form.get("status", "Pending"),
        "receiving_date":  form.get("receiving_date") or None,
        "delivery_date":   form.get("delivery_date") or None,
        "paper_cost":      paper,
        "printing_cost":   printing,
        "design_cost":     design,
        "binding_cost":    binding,
        "other_charges":   other,
        "total_cost":      total,   # ✅ explicitly set
    }


def create_job(form: dict) -> dict:
    db = get_db()
    job_id  = generate_job_id()
    job_row = _build_job_row(form)
    job_row["job_id"]    = job_id
    job_row["job_image"] = form.get("job_image", "")

    job = db.table("jobs").insert(job_row).execute().data[0]
    _upsert_job_details(db, job["id"], form)
    return job


def update_job(job_pk: int, form: dict):
    db = get_db()
    job_row = _build_job_row(form)

    # Only update image if a new one was uploaded
    if form.get("job_image"):
        job_row["job_image"] = form.get("job_image")

    db.table("jobs").update(job_row).eq("id", job_pk).execute()
    _upsert_job_details(db, job_pk, form)


def delete_job(job_pk: int):
    db = get_db()
    db.table("jobs").delete().eq("id", job_pk).execute()


def duplicate_job(job_pk: int) -> dict:
    """Repeat/duplicate a previous job with a new job_id."""
    job     = get_job(job_pk)
    details = get_job_details(job_pk)
    merged  = {**job, **details}
    merged.pop("id", None)
    merged.pop("job_id", None)
    merged.pop("created_at", None)
    merged.pop("updated_at", None)
    merged.pop("customers", None)
    merged["status"]         = "Pending"
    merged["receiving_date"] = None
    merged["delivery_date"]  = None
    return create_job(merged)


def _upsert_job_details(db, job_pk: int, form: dict):
    detail_row = {
        "job_id":               job_pk,
        # Printing
        "machine":              form.get("machine", ""),
        "size_printing":        form.get("size_printing", ""),
        "color":                form.get("color", ""),
        "color_details":        form.get("color_details", ""),
        "backside_printing":    form.get("backside_printing") == "yes",
        "back_color":           form.get("back_color", ""),
        "total_printing":       form.get("total_printing", ""),
        "total_sets":           form.get("total_sets", ""),
        # Plate
        "plate_provider":       form.get("plate_provider", ""),
        "plate_type":           form.get("plate_type", ""),
        "plate_size":           form.get("plate_size", ""),
        # Design
        "design_size":          form.get("design_size", ""),
        "design_pages":         form.get("design_pages", ""),
        "design_details":       form.get("design_details", ""),
        # Lamination
        "lam_provider":         form.get("lam_provider", ""),
        "lam_type":             form.get("lam_type", ""),
        "lam_size":             form.get("lam_size", ""),
        "lam_quantity":         form.get("lam_quantity", ""),
        "lam_spot_quantity":    form.get("lam_spot_quantity", ""),
        # Punching
        "punch_provider":       form.get("punch_provider", ""),
        "punch_size":           form.get("punch_size", ""),
        "punch_quantity":       form.get("punch_quantity", ""),
        # Creasing
        "crease_provider":      form.get("crease_provider", ""),
        "crease_type":          form.get("crease_type", ""),
        "crease_size":          form.get("crease_size", ""),
        "crease_quantity":      form.get("crease_quantity", ""),
        # Folding
        "fold_provider":        form.get("fold_provider", ""),
        "fold_size":            form.get("fold_size", ""),
        "fold_quantity":        form.get("fold_quantity", ""),
        # Paper
        "paper_provider":       form.get("paper_provider", ""),
        "paper_size":           form.get("paper_size", ""),
        "paper_sheets":         form.get("paper_sheets", ""),
        "paper_type":           form.get("paper_type", ""),
        "paper_gsm":            form.get("paper_gsm", ""),
        # Binding
        "bind_provider":        form.get("bind_provider", ""),
        "bind_type":            form.get("bind_type", ""),
        "bind_size":            form.get("bind_size", ""),
        "bind_pages":           form.get("bind_pages", ""),
        "bind_quantity":        form.get("bind_quantity", ""),
        # Envelope
        "env_provider":         form.get("env_provider", ""),
        "env_type":             form.get("env_type", ""),
        "env_size":             form.get("env_size", ""),
        "env_quantity":         form.get("env_quantity", ""),
        # Cutting / Other
        "cutting_instructions": form.get("cutting_instructions", ""),
        "other_instructions":   form.get("other_instructions", ""),
    }
    existing = db.table("job_details").select("id").eq("job_id", job_pk).execute()
    if existing.data:
        db.table("job_details").update(detail_row).eq("job_id", job_pk).execute()
    else:
        db.table("job_details").insert(detail_row).execute()


# ══════════════════════════════════════════
#  DASHBOARD STATS
# ══════════════════════════════════════════

def get_dashboard_stats() -> dict:
    db = get_db()
    from datetime import date

    today       = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()
    year_start  = date.today().replace(month=1, day=1).isoformat()

    total     = db.table("jobs").select("id", count="exact").execute().count or 0
    pending   = db.table("jobs").select("id", count="exact").eq("status", "Pending").execute().count or 0
    inprog    = db.table("jobs").select("id", count="exact").eq("status", "In Progress").execute().count or 0
    completed = db.table("jobs").select("id", count="exact").eq("status", "Completed").execute().count or 0
    delivered = db.table("jobs").select("id", count="exact").eq("status", "Delivered").execute().count or 0

    # Daily revenue
    today_jobs = db.table("jobs").select("total_cost").eq("receiving_date", today).execute().data or []
    daily_rev  = sum(safe_float(j.get("total_cost", 0)) for j in today_jobs)

    # Monthly revenue
    month_jobs  = db.table("jobs").select("total_cost").gte("receiving_date", month_start).execute().data or []
    monthly_rev = sum(safe_float(j.get("total_cost", 0)) for j in month_jobs)

    # Yearly revenue
    year_jobs  = db.table("jobs").select("total_cost").gte("receiving_date", year_start).execute().data or []
    yearly_rev = sum(safe_float(j.get("total_cost", 0)) for j in year_jobs)

    # All-time total revenue
    all_jobs  = db.table("jobs").select("total_cost").execute().data or []
    total_rev = sum(safe_float(j.get("total_cost", 0)) for j in all_jobs)

    recent = db.table("jobs").select(
        "*, customers(name)"
    ).order("created_at", desc=True).limit(8).execute().data

    return {
        "total": total, "pending": pending, "in_progress": inprog,
        "completed": completed, "delivered": delivered,
        "daily_revenue":   round(daily_rev, 2),
        "monthly_revenue": round(monthly_rev, 2),
        "yearly_revenue":  round(yearly_rev, 2),
        "total_revenue":   round(total_rev, 2),
        "recent_jobs":     recent,
    }