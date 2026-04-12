import os
from werkzeug.utils import secure_filename
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify, Response, send_file)
from dotenv import load_dotenv
from auth import login_required, check_credentials
from utils import (generate_qr_base64, status_badge_class, safe_float,
                   upload_image_to_supabase, generate_job_pdf)
import models
import io

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

# ── Jinja helpers ────────────────────────────────────────────────
app.jinja_env.globals["status_badge_class"] = status_badge_class

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def handle_image_upload(request_files) -> str:
    """
    Handles image upload → Supabase Storage.
    Returns public URL string, or '' if no file.
    """
    file = request_files.get("job_image")
    if not file or not file.filename:
        return ""
    if not allowed_file(file.filename):
        flash("Invalid image format. Use PNG/JPG/JPEG/GIF/WEBP.", "warning")
        return ""
    filename = secure_filename(file.filename)
    file_bytes = file.read()
    url = upload_image_to_supabase(file_bytes, filename)
    if not url:
        # Fallback: local storage (dev only — won't persist on Render)
        UPLOAD_FOLDER = "static/uploads"
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        local_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        flash("Image saved locally (Supabase Storage not configured).", "warning")
        return f"/static/uploads/{filename}"
    return url


# ══════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if check_credentials(username, password):
            session["logged_in"] = True
            session["admin_user"] = username
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials. Please try again.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════

@app.route("/dashboard")
@login_required
def dashboard():
    stats = models.get_dashboard_stats()
    return render_template("dashboard.html", **stats)


# ══════════════════════════════════════════════════════════════════
#  CUSTOMERS
# ══════════════════════════════════════════════════════════════════

@app.route("/customers")
@login_required
def customers():
    q         = request.args.get("q", "").strip()
    cust_list = models.search_customers(q) if q else models.get_all_customers()
    return render_template("customers.html", customers=cust_list, query=q)


@app.route("/customers/new", methods=["GET", "POST"])
@login_required
def customer_new():
    if request.method == "POST":
        models.create_customer(
            request.form["name"].strip(),
            request.form["mobile"].strip(),
            request.form.get("address", "").strip()
        )
        flash("Customer added successfully.", "success")
        return redirect(url_for("customers"))
    return render_template("customer_form.html", customer=None)


@app.route("/customers/<int:cid>/edit", methods=["GET", "POST"])
@login_required
def customer_edit(cid):
    customer = models.get_customer(cid)
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for("customers"))
    if request.method == "POST":
        models.update_customer(
            cid,
            request.form["name"].strip(),
            request.form["mobile"].strip(),
            request.form.get("address", "").strip()
        )
        flash("Customer updated.", "success")
        return redirect(url_for("customers"))
    return render_template("customer_form.html", customer=customer)


@app.route("/customers/<int:cid>/delete", methods=["POST"])
@login_required
def customer_delete(cid):
    models.delete_customer(cid)
    flash("Customer deleted.", "info")
    return redirect(url_for("customers"))


@app.route("/customers/<int:cid>/history")
@login_required
def customer_history(cid):
    customer  = models.get_customer(cid)
    job_list  = models.get_customer_jobs(cid)
    return render_template("customer_history.html",
                           customer=customer, jobs=job_list)


@app.route("/api/customers/search")
@login_required
def api_customer_search():
    q    = request.args.get("q", "").strip()
    data = models.search_customers(q) if q else []
    return jsonify(data)


# ══════════════════════════════════════════════════════════════════
#  JOBS
# ══════════════════════════════════════════════════════════════════

@app.route("/jobs")
@login_required
def jobs():
    status    = request.args.get("status", "").strip()
    job_list  = models.get_all_jobs(status_filter=status or None)
    return render_template("jobs.html", jobs=job_list, status_filter=status)


@app.route("/jobs/new", methods=["GET", "POST"])
@login_required
def job_new():
    customers = models.get_all_customers()

    if request.method == "POST":
        form_data = dict(request.form)
        image_url = handle_image_upload(request.files)
        if image_url:
            form_data["job_image"] = image_url

        job = models.create_job(form_data)
        flash(f"Job {job['job_id']} created successfully!", "success")
        return redirect(url_for("job_sheet", job_pk=job["id"]))

    return render_template("job_form.html",
                           job=None, details=None,
                           customers=customers, is_edit=False)


@app.route("/jobs/<int:job_pk>/edit", methods=["GET", "POST"])
@login_required
def job_edit(job_pk):
    job       = models.get_job(job_pk)
    details   = models.get_job_details(job_pk)
    customers = models.get_all_customers()

    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))

    if request.method == "POST":
        form_data = dict(request.form)
        image_url = handle_image_upload(request.files)
        if image_url:
            form_data["job_image"] = image_url

        models.update_job(job_pk, form_data)
        flash("Job updated successfully.", "success")
        return redirect(url_for("job_sheet", job_pk=job_pk))

    return render_template("job_form.html",
                           job=job, details=details,
                           customers=customers, is_edit=True)


@app.route("/jobs/<int:job_pk>/delete", methods=["POST"])
@login_required
def job_delete(job_pk):
    models.delete_job(job_pk)
    flash("Job deleted.", "info")
    return redirect(url_for("jobs"))


@app.route("/jobs/<int:job_pk>/duplicate", methods=["POST"])
@login_required
def job_duplicate(job_pk):
    new_job = models.duplicate_job(job_pk)
    flash(f"Job duplicated as {new_job['job_id']}.", "success")
    return redirect(url_for("job_edit", job_pk=new_job["id"]))


@app.route("/jobs/<int:job_pk>/sheet")
@login_required
def job_sheet(job_pk):
    job     = models.get_job(job_pk)
    details = models.get_job_details(job_pk)
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))
    qr_data = f"Job ID: {job['job_id']} | {job.get('job_name','')} | Status: {job.get('status','')}"
    qr_b64  = generate_qr_base64(qr_data)
    return render_template("job_sheet.html",
                           job=job, details=details, qr_b64=qr_b64)


@app.route("/jobs/<int:job_pk>/pdf")
@login_required
def job_pdf(job_pk):
    """Download job sheet as PDF with grand total."""
    job     = models.get_job(job_pk)
    details = models.get_job_details(job_pk)
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))
    try:
        pdf_bytes = generate_job_pdf(job, details)
        filename  = f"job_{job.get('job_id','sheet')}.pdf"
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        flash(f"PDF generation failed: {e}", "danger")
        return redirect(url_for("job_sheet", job_pk=job_pk))


@app.route("/jobs/<int:job_pk>/status", methods=["POST"])
@login_required
def job_status_update(job_pk):
    new_status = request.form.get("status")
    if new_status in ("Pending", "In Progress", "Completed", "Delivered"):
        existing_job     = models.get_job(job_pk)
        existing_details = models.get_job_details(job_pk)
        merged = {**existing_job, **existing_details, "status": new_status}
        models.update_job(job_pk, merged)
        flash(f"Status updated to {new_status}.", "success")
    return redirect(request.referrer or url_for("jobs"))


# ══════════════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True)