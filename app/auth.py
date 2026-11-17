"""Login, registration and password recovery."""

import re
import secrets
from datetime import datetime, timedelta

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .services import notify, now_iso

bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
RESET_MINUTES = 15


def _safe_target(target, fallback):
    """Only allow same-site redirects."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return fallback


def _password_problem(password, confirm=None):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must include both letters and numbers."
    if confirm is not None and password != confirm:
        return "Passwords do not match."
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.get("user"):
        destination = "admin.dashboard" if g.user["role"] == "admin" else "shop.home"
        return redirect(url_for(destination))

    identifier = ""
    remember = False

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"
        errors = []

        if not identifier:
            errors.append("Enter your username or email.")
        if not password:
            errors.append("Enter your password.")

        user = None
        if not errors:
            user = get_db().execute(
                "SELECT * FROM users WHERE lower(username) = lower(?) OR lower(email) = lower(?)",
                (identifier, identifier),
            ).fetchone()
            if user is None or not check_password_hash(user["password_hash"], password):
                errors.append("Incorrect username or password.")
            elif not user["is_active"]:
                errors.append("This account is deactivated. Please contact the administrator.")

        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("auth/login.html", identifier=identifier, remember=remember), 400

        session.clear()
        session["user_id"] = user["id"]
        session.permanent = remember
        flash(f"Welcome back, {user['full_name'].split()[0]}!", "success")

        if user["role"] == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(_safe_target(request.args.get("next"), url_for("shop.home")))

    return render_template("auth/login.html", identifier=identifier, remember=remember)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.get("user"):
        return redirect(url_for("shop.home"))

    form = {}

    if request.method == "POST":
        form = {
            "full_name": request.form.get("full_name", "").strip(),
            "username": request.form.get("username", "").strip(),
            "email": request.form.get("email", "").strip().lower(),
        }
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        errors = []

        if len(form["full_name"]) < 3:
            errors.append("Enter your full name (at least 3 characters).")
        if not USERNAME_RE.match(form["username"]):
            errors.append("Username must be 3-20 characters using letters, numbers, dot or underscore.")
        if not EMAIL_RE.match(form["email"]):
            errors.append("Enter a valid email address.")
        password_error = _password_problem(password, confirm)
        if password_error:
            errors.append(password_error)

        db = get_db()
        if not errors:
            if db.execute("SELECT 1 FROM users WHERE lower(username) = lower(?)",
                          (form["username"],)).fetchone():
                errors.append("That username is already taken.")
            if db.execute("SELECT 1 FROM users WHERE lower(email) = lower(?)",
                          (form["email"],)).fetchone():
                errors.append("An account with that email already exists.")

        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("auth/register.html", form=form), 400

        cursor = db.execute(
            """INSERT INTO users (full_name, username, email, password_hash, role, created_at)
               VALUES (?, ?, ?, ?, 'customer', ?)""",
            (form["full_name"], form["username"], form["email"],
             generate_password_hash(password), now_iso()),
        )
        user_id = cursor.lastrowid
        notify(user_id, "Welcome to ByteBodega",
               "Your account is ready. Browse the catalogue, save favourites and track your orders here.")
        db.commit()

        session.clear()
        session["user_id"] = user_id
        session.permanent = False
        flash("Account created. Happy shopping!", "success")
        return redirect(url_for("shop.home"))

    return render_template("auth/register.html", form=form)


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not EMAIL_RE.match(email):
            flash("Enter the email address linked to your account.", "error")
            return render_template("auth/forgot.html", email=email), 400

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
        if user is None:
            flash("No account was found with that email address.", "error")
            return render_template("auth/forgot.html", email=email), 404

        code = f"{secrets.randbelow(900000) + 100000}"
        expires = (datetime.now() + timedelta(minutes=RESET_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute("UPDATE users SET reset_code = ?, reset_expires = ? WHERE id = ?",
                   (code, expires, user["id"]))
        db.commit()
        flash("Reset code generated. Enter it below with your new password.", "success")
        return redirect(url_for("auth.reset_password", email=email))

    return render_template("auth/forgot.html", email="")


@bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = request.values.get("email", "").strip().lower()
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email,)).fetchone() \
        if email else None
    demo_code = None
    if user and user["reset_code"] and user["reset_expires"]:
        if datetime.strptime(user["reset_expires"], "%Y-%m-%d %H:%M:%S") > datetime.now():
            demo_code = user["reset_code"]

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if user is None:
            flash("Start again by entering your account email.", "error")
            return redirect(url_for("auth.forgot_password"))
        if not user["reset_code"] or not user["reset_expires"]:
            flash("No active reset code. Request a new one.", "error")
            return redirect(url_for("auth.forgot_password"))
        if datetime.strptime(user["reset_expires"], "%Y-%m-%d %H:%M:%S") <= datetime.now():
            flash("That reset code has expired. Request a new one.", "error")
            return redirect(url_for("auth.forgot_password"))
        if code != user["reset_code"]:
            flash("That reset code is not correct.", "error")
            return render_template("auth/reset.html", email=email, demo_code=demo_code), 400

        password_error = _password_problem(password, confirm)
        if password_error:
            flash(password_error, "error")
            return render_template("auth/reset.html", email=email, demo_code=demo_code), 400

        db.execute("UPDATE users SET password_hash = ?, reset_code = NULL, reset_expires = NULL "
                   "WHERE id = ?", (generate_password_hash(password), user["id"]))
        notify(user["id"], "Password changed",
               "Your password was reset successfully. If this was not you, contact support.")
        db.commit()
        flash("Password updated. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset.html", email=email, demo_code=demo_code)


@bp.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
