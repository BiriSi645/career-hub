from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from email_validator import EmailNotValidError, validate_email

from app.forms import local_redirect_target, text_field
from app.models import users

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            email = validate_email(email, check_deliverability=False).normalized.lower()
            first = text_field(request.form, "first_name", 80, required=True)
            last = text_field(request.form, "last_name", 80, required=True)
            if len(email) > 255 or not 8 <= len(password) <= 128:
                raise ValueError("Use a valid email and a password with 8 to 128 characters.")
            role = request.form.get("account_type", "jobseeker")
            if role not in {"jobseeker", "recruiter"}:
                raise ValueError("Choose a valid account type.")
        except (EmailNotValidError, ValueError) as exc:
            flash(str(exc), "danger")
            return render_template("auth/register.html"), 400
        user = users.create_account(email, password, first, last, role)
        if user is None:
            flash("Email is already registered.", "danger")
        else:
            login_user(user)
            flash("Welcome to Career Hub!", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            email = validate_email(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            # Existing local demo accounts use a reserved domain.
            pass
        user = users.find_user_by_email(email) if len(email) <= 255 and "\x00" not in email else None
        if (
            user
            and len(password) <= 128
            and user.check_password(password)
            and user.is_active
        ):
            login_user(user, remember=bool(request.form.get("remember")))
            return redirect(local_redirect_target(request.args.get("next")) or url_for("main.dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html")


@auth_bp.post("/logout")
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    destination = "auth.login" if request.form.get("switch_account") == "1" else "main.index"
    return redirect(url_for(destination))
