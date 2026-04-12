# 🖨️ PrintShop Management System

A full-featured printing shop job management web application built with **Flask + Supabase**.

---

## 📁 Project Structure

```
printing_shop/
├── app.py              ← Flask routes & app entry point
├── auth.py             ← Admin login/logout logic
├── db.py               ← Supabase client connection
├── models.py           ← All database operations (CRUD)
├── utils.py            ← Job ID generator, QR code, cost calc
├── Procfile            ← For Render deployment
├── render.yaml         ← Render config
├── requirements.txt    ← Python dependencies
├── schema.sql          ← Run this in Supabase SQL Editor
├── .env                ← Your secrets (DO NOT commit)
└── templates/
    ├── base.html           ← Master layout + sidebar
    ├── login.html          ← Admin login page
    ├── dashboard.html      ← Stats + recent jobs
    ├── customers.html      ← Customer list + search
    ├── customer_form.html  ← Add/Edit customer
    ├── customer_history.html ← Customer job history
    ├── jobs.html           ← All jobs with filter tabs
    ├── job_form.html       ← Full job entry form (all sections)
    └── job_sheet.html      ← A4 printable job sheet 🔥
```

---

## 🚀 Setup Guide

### Step 1 — Supabase Database

1. Go to [supabase.com](https://supabase.com) → New Project
2. Open **SQL Editor** → **New Query**
3. Paste the contents of `schema.sql` → Run
4. Go to **Settings → API** and copy:
   - Project URL → `SUPABASE_URL`
   - `service_role` key → `SUPABASE_KEY` *(use service_role for full access)*

### Step 2 — Configure `.env`

```env
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=your_service_role_key_here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=yourpassword123
SECRET_KEY=any-long-random-string-here
FLASK_ENV=production
```

### Step 3 — Run Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Open: http://localhost:5000

---

## ☁️ Deploy on Render (Free)

1. Push your code to **GitHub** (make sure `.env` is in `.gitignore`)
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`
5. Add **Environment Variables** (same as your `.env`):
   - `SUPABASE_URL`, `SUPABASE_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY`
6. Deploy! 🎉

---

## 📊 Supabase Free Tier — Storage Capacity

| Resource         | Free Tier Limit   | Estimated Capacity              |
|------------------|-------------------|---------------------------------|
| Database Storage | 500 MB            | ~50,000+ full job records       |
| API Requests     | Unlimited         | No cap on reads/writes          |
| Users/Data       | Unlimited rows    | Only storage size matters       |
| Bandwidth        | 5 GB/month        | More than enough for a shop     |

**For 1 printing shop:** Free tier will last **years** before you need to upgrade.

---

## ✨ Features

- 🔐 Admin login/logout with session
- 👥 Customer management (add/edit/delete/search)
- 📋 Full job sheet with 13 sections (Printing, Plate, Design, Lamination, Punching, Creasing, Folding, Paper, Binding, Envelope, Cutting, Other)
- 🖨️ A4 printable job sheet with QR code
- 💰 Auto cost calculation
- 🔁 Repeat/duplicate previous jobs
- 📊 Dashboard with live stats
- 🏷️ Status filter (Pending / In Progress / Completed / Delivered)
- 📱 Mobile-responsive sidebar

---

## 🔑 Default Login

```
Username: admin
Password: admin@123
```
*(Change in `.env` before deploying!)*