from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.clock import local_today
from app.forms import text_field
from app.models import jobs as job_model

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    today = local_today()
    return render_template("index.html", jobs=job_model.latest_postings(today), counts=job_model.homepage_counts(today))


@main_bp.get("/jobs")
def jobs():
    try:
        q = text_field(request.args, "q", 160) or ""
    except ValueError:
        flash("Enter a search term of at most 160 characters.", "warning")
        return redirect(url_for("main.jobs"))
    postings = job_model.search_postings(
        q,
        request.args.get("category", type=int),
        request.args.get("type"),
        local_today(),
        filter_category=bool(request.args.get("category")),
    )
    categories = job_model.list_categories()
    return render_template(
        "jobs/list.html",
        jobs=postings,
        categories=categories,
        q=q,
    )


@main_bp.get("/jobs/<int:job_id>")
def job_detail(job_id):
    job = job_model.find_public_posting(job_id, local_today())
    if job is None:
        abort(404)
    is_saved = False
    resumes = []
    if current_user.is_authenticated and current_user.has_role("jobseeker"):
        is_saved = job_model.is_posting_saved(current_user.id, job_id)
        resumes = job_model.list_resume_choices(current_user.id)
    return render_template("jobs/detail.html", job=job, is_saved=is_saved, resumes=resumes,
                           skills=job_model.required_skills(job_id))


@main_bp.get("/dashboard")
@login_required
def dashboard():
    if current_user.has_role("admin"):
        return redirect(url_for("admin.dashboard"))
    if current_user.has_role("recruiter"):
        return redirect(url_for("company.dashboard"))
    return redirect(url_for("seeker.dashboard"))
