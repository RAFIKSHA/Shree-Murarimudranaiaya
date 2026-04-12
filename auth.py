import os
from functools import wraps
from flask import session, redirect, url_for, flash
from dotenv import load_dotenv

load_dotenv()

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin@123")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def check_credentials(username: str, password: str) -> bool:
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD