from psycopg import IntegrityError
from re import fullmatch
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from app.clock import local_today
from app.authz import roles_required
from app.models import candidates
from app.services import candidates as candidate_service
from app.models.jobs import find_public_posting
from app.forms import date_field, number_field, public_http_url, text_field
from app.services.jobs import PROFICIENCIES
from app.services.applications import submit_application
from app.services.resumes import (
    BLOB_FILE_PREFIX,
    delete_resume_file,
    resume_file_response,
    save_resume_file,
)

seeker_bp = Blueprint("seeker", __name__)


@seeker_bp.get("/dashboard")
@roles_required("jobseeker")
def dashboard():
    counts = candidates.dashboard_counts(current_user.id)
    return render_template("seeker/dashboard.html", counts=counts,
                           applications=candidates.list_candidate_applications(current_user.id))


@seeker_bp.route("/profile", methods=["GET", "POST"])
@roles_required("jobseeker")
def profile():
    params = {"user_id": current_user.id}
    if request.method == "POST":
        try:
            limits = {"headline": 160, "bio": 10000, "city": 100, "country": 100,
                      "linkedin_url": 255, "portfolio_url": 255}
            details = {field: text_field(request.form, field, limit) for field, limit in limits.items()}
            for field in ("linkedin_url", "portfolio_url"):
                if details[field] and not public_http_url(details[field]):
                    raise ValueError("Profile links must start with http:// or https://.")
            phone = text_field(request.form, "phone", 30) if "phone" in request.form else current_user.phone
            if phone and (not fullmatch(r"[+0-9() .-]+", phone) or not any(char.isdecimal() for char in phone)):
                raise ValueError("Enter a valid phone number.")
            candidate_service.update_profile(
                current_user.id, text_field(request.form, "first_name", 80, required=True),
                text_field(request.form, "last_name", 80, required=True),
                phone, details,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Profile updated.", "success")
        return redirect(url_for("seeker.profile"))
    candidate = candidates.find_profile(params)
    education = candidates.list_education(params)
    experience = candidates.list_experience(params)
    resumes = candidates.list_resumes(params)
    candidate_skills = candidates.list_candidate_skills(params)
    available_skills = candidates.list_available_skills(params)
    return render_template("seeker/profile.html", candidate=candidate, education=education,
                           experience=experience, resumes=resumes, candidate_skills=candidate_skills,
                           skills=available_skills)


@seeker_bp.post("/skills")
@roles_required("jobseeker")
def add_skill():
    skill_id = request.form.get("skill_id", type=int)
    proficiency = request.form.get("proficiency", "intermediate")
    params = {"skill_id": skill_id, "user_id": current_user.id}
    skill = candidates.find_skill_for_candidate(params)
    if skill is None:
        flash("Choose a skill.", "warning")
    elif skill.already_added:
        flash("That skill is already on your profile.", "warning")
    elif proficiency not in PROFICIENCIES:
        flash("Choose a valid proficiency level.", "danger")
    else:
        try:
            years_experience = number_field(request.form, "years_experience", 999.9, 1) or 0
            candidates.insert_candidate_skill({**params, "proficiency": proficiency, "years": years_experience})
        except ValueError as exc:
            flash(str(exc), "danger")
        except IntegrityError:
            flash("This skill is no longer available.", "danger")
        else:
            flash(f"{skill.name} added to your profile.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/skills/<int:skill_id>/delete")
@roles_required("jobseeker")
def delete_skill(skill_id):
    removed = candidates.remove_candidate_skill(current_user.id, skill_id)
    if removed:
        flash("Skill removed.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/education")
@roles_required("jobseeker")
def add_education():
    try:
        start, end = dates_from_form()
        candidates.insert_education(
            current_user.id, text_field(request.form, "institution", 180, required=True),
            text_field(request.form, "degree", 120, required=True),
            text_field(request.form, "field_of_study", 120), start, end,
        )
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Education added.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/experience")
@roles_required("jobseeker")
def add_experience():
    try:
        start, end = dates_from_form()
        candidates.insert_experience(
            current_user.id, text_field(request.form, "company_name", 160, required=True),
            text_field(request.form, "title", 120, required=True), start, end,
        )
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Experience added.", "success")
    return redirect(url_for("seeker.profile"))


def dates_from_form():
    start = date_field(request.form, "start_date", required=True)
    end = date_field(request.form, "end_date")
    if end and end < start:
        raise ValueError("End date must be on or after the start date.")
    return start, end


@seeker_bp.post("/resumes")
@roles_required("jobseeker")
def add_resume():
    file_url = None
    try:
        upload = request.files.get("resume_file")
        title = text_field(request.form, "title", 120)
        file_url = save_resume_file(upload)
        if not title:
            title = upload.filename.rsplit(".", 1)[0].replace("\x00", "").strip()[:120] or "CV"
        candidate_service.save_resume(current_user.id, title, file_url, bool(request.form.get("is_primary")))
        flash("CV uploaded.", "success")
    except ValueError as exc:
        _discard_resume_upload(file_url)
        flash(str(exc), "danger")
    except IntegrityError:
        _discard_resume_upload(file_url)
        flash("The CV could not be saved.", "danger")
    except OSError:
        _discard_resume_upload(file_url)
        flash("The CV file could not be stored. Try again later.", "danger")
    except Exception:
        _discard_resume_upload(file_url)
        raise
    return redirect(url_for("seeker.profile"))


def _discard_resume_upload(file_url):
    if file_url:
        try:
            delete_resume_file(file_url)
        except OSError:
            current_app.logger.warning("Could not clean up an unregistered CV upload.")


@seeker_bp.get("/resumes/<int:resume_id>/file")
@roles_required("jobseeker")
def resume_file(resume_id):
    resume = candidates.find_owned_resume(resume_id, current_user.id)
    if resume is None:
        abort(404)
    return resume_file_response(resume)


@seeker_bp.post("/resumes/<int:resume_id>/primary")
@roles_required("jobseeker")
def set_primary_resume(resume_id):
    title = candidate_service.choose_primary_resume(current_user.id, resume_id)
    if title is None:
        abort(404)
    flash(f"{title} is now your primary CV.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/resumes/<int:resume_id>/delete")
@roles_required("jobseeker")
def delete_resume(resume_id):
    try:
        resume = candidate_service.delete_resume(current_user.id, resume_id)
    except OSError:
        flash("The CV could not be deleted. Try again later.", "warning")
        return redirect(url_for("seeker.profile"))
    if resume is None:
        abort(404)
    try:
        if not resume.file_url.startswith(BLOB_FILE_PREFIX):
            delete_resume_file(resume.file_url)
    except OSError:
        flash("The CV record was removed. The file could not be cleaned up.", "warning")
    else:
        flash("CV deleted.", "success")
    return redirect(url_for("seeker.profile"))


@seeker_bp.post("/jobs/<int:job_id>/save")
@roles_required("jobseeker")
def save_job(job_id):
    if find_public_posting(job_id, local_today()) is None:
        abort(404)
    try:
        saved = candidate_service.toggle_bookmark(current_user.id, job_id)
    except IntegrityError:
        flash("This job is no longer available.", "warning")
        return redirect(url_for("main.jobs"))
    flash("Job saved." if saved else "Job unsaved.", "success" if saved else "info")
    if request.form.get("return_to") == "saved":
        return redirect(url_for("seeker.saved"))
    return redirect(url_for("main.job_detail", job_id=job_id))


@seeker_bp.post("/jobs/<int:job_id>/apply")
@roles_required("jobseeker")
def apply(job_id):
    try:
        resume_id = request.form.get("resume_id", type=int)
        if request.form.get("resume_id") and (resume_id is None or not 1 <= resume_id <= 2147483647):
            raise ValueError("Choose a valid CV.")
        submit_application(
            current_user,
            job_id,
            resume_id,
            text_field(request.form, "cover_letter", 10000),
        )
        flash("Application submitted.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    except IntegrityError:
        flash("Could not submit this application. Check the posting and CV and try again.", "danger")
    return redirect(url_for("main.job_detail", job_id=job_id))


@seeker_bp.get("/applications")
@roles_required("jobseeker")
def applications():
    return render_template(
        "seeker/applications.html",
        applications=candidates.list_candidate_applications(current_user.id),
    )


@seeker_bp.get("/applications/<int:application_id>")
@roles_required("jobseeker")
def application_detail(application_id):
    params = {"id": application_id, "user_id": current_user.id}
    application = candidates.find_owned_application(params)
    if application is None:
        abort(404)
    history = candidates.list_application_history(params)
    interviews = candidates.list_application_interviews(params)
    return render_template("seeker/application_detail.html", application=application,
                           history=history, interviews=interviews)


@seeker_bp.get("/saved")
@roles_required("jobseeker")
def saved():
    jobs = candidates.list_bookmarks(current_user.id)
    return render_template(
        "seeker/saved.html",
        saved=jobs,
    )


@seeker_bp.get("/notifications")
@roles_required("jobseeker")
def notifications():
    return render_template("seeker/notifications.html", notices=candidates.list_notifications(current_user.id))


@seeker_bp.post("/notifications/<int:notification_id>/read")
@roles_required("jobseeker")
def read_notification(notification_id):
    if not candidates.mark_notification_read(current_user.id, notification_id):
        abort(404)
    return redirect(url_for("seeker.notifications"))
