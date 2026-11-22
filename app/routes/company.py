from types import SimpleNamespace
from psycopg import IntegrityError
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from app.clock import local_today
from app.authz import company_membership, roles_required
from app.forms import date_field, number_field, public_http_url, text_field
from app.models import companies as company_model, jobs as job_model
from app.services.applications import (
    TRANSITIONS,
    ApplicationError,
    update_application_status,
)
from app.services.jobs import (
    EMPLOYMENT_TYPES, PROFICIENCIES, WORKPLACE_TYPES, create_posting, delete_or_close_posting,
)
from app.services.resumes import resume_file_response
from app.services.interviews import INTERVIEW_STATUSES, change_interview_status, schedule_interview as book_interview
from app.models.candidates import list_application_interviews

company_bp = Blueprint("company", __name__)


@company_bp.errorhandler(403)
def forbidden(error):
    return render_template("company/forbidden.html"), 403


def staff_or_403(company_id, manage=False):
    membership = company_membership(company_id, manage)
    if not membership:
        abort(403)
    return membership


def company_job(job_id):
    job = company_model.find_job(job_id)
    if job is None:
        abort(404)
    staff_or_403(job.company_id)
    return job


def company_application(application_id):
    application = company_model.find_application(application_id)
    if application is None:
        abort(404)
    staff_or_403(application.company_id)
    return SimpleNamespace(**application._asdict())


def company_details():
    limits = {"name": 160, "industry": 120, "description": 12000, "website": 255, "city": 100, "country": 100}
    details = {field: text_field(request.form, field, limit, required=field == "name")
               for field, limit in limits.items()}
    details["country"] = details["country"] or "Türkiye"
    if details["website"] and not public_http_url(details["website"]):
        raise ValueError("Website must start with http:// or https://.")
    return details


@company_bp.get("/dashboard")
@roles_required("recruiter")
def dashboard():
    params = {"user_id": current_user.id}
    memberships = company_model.list_memberships(params)
    jobs = company_model.list_staff_postings(params)
    return render_template("company/dashboard.html", memberships=memberships, jobs=jobs)


@company_bp.route("/new", methods=["GET", "POST"])
@roles_required("recruiter")
def create_company():
    if request.method == "POST":
        try:
            company_model.create_company(current_user.id, company_details())
        except ValueError as exc:
            flash(str(exc), "danger")
        except IntegrityError:
            flash("A company with this name already exists.", "danger")
        else:
            flash("Company created.", "success")
            return redirect(url_for("company.dashboard"))
    return render_template("company/form.html", company=None)


@company_bp.get("/<int:company_id>")
@roles_required("recruiter")
def company_profile(company_id):
    membership = staff_or_403(company_id)
    company = company_model.find_company(company_id)
    if company is None:
        abort(404)
    return render_template("company/profile.html", company=company, membership=membership)


@company_bp.route("/<int:company_id>/edit", methods=["GET", "POST"])
@roles_required("recruiter")
def edit_company(company_id):
    staff_or_403(company_id, True)
    if request.method == "POST":
        try:
            company_model.update_company({**company_details(), "id": company_id})
        except ValueError as exc:
            flash(str(exc), "danger")
        except IntegrityError:
            flash("A company with this name already exists.", "danger")
        else:
            flash("Company updated.", "success")
            return redirect(url_for("company.company_profile", company_id=company_id))
        return redirect(url_for("company.edit_company", company_id=company_id))
    company = company_model.find_company(company_id)
    return render_template("company/form.html", company=company)


@company_bp.route("/<int:company_id>/jobs/new", methods=["GET", "POST"])
@roles_required("recruiter")
def create_job(company_id):
    staff_or_403(company_id)
    categories = job_model.list_categories()
    skills = job_model.skill_catalog()
    today = local_today()
    if request.method == "POST":
        try:
            category_id = request.form.get("category_id", type=int)
            if category_id not in {category.id for category in categories}:
                raise ValueError("Choose a valid category.")
            deadline = date_field(request.form, "deadline")
            if deadline and deadline < today:
                raise ValueError("Application deadline cannot be in the past.")
            minimum = number_field(request.form, "salary_min", 9999999999.99, 2)
            maximum = number_field(request.form, "salary_max", 9999999999.99, 2)
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError("Maximum salary must be at least the minimum salary.")

            employment = request.form.get("employment_type")
            workplace = request.form.get("workplace_type")
            status = request.form.get("status", "open")
            if employment not in EMPLOYMENT_TYPES or workplace not in WORKPLACE_TYPES or status not in {"draft", "open"}:
                raise ValueError("Choose valid posting options.")

            selected = request.form.getlist("skill_id")
            known = {str(skill.id) for skill in skills}
            if len(selected) != len(set(selected)) or not set(selected) <= known:
                raise ValueError("Choose valid skills once each.")
            requirements = []
            for skill_id in selected:
                level = request.form.get(f"level_{skill_id}", "intermediate")
                if level not in PROFICIENCIES:
                    raise ValueError("Choose a valid proficiency level for each skill.")
                requirements.append((int(skill_id), request.form.get(f"mandatory_{skill_id}") == "on", level))

            details = {
                "company_id": company_id, "category_id": category_id, "created_by": current_user.id,
                "title": text_field(request.form, "title", 160, required=True),
                "description": text_field(request.form, "description", 12000, required=True),
                "location": text_field(request.form, "location", 120, required=True),
                "requirements": text_field(request.form, "requirements", 12000),
                "employment_type": employment, "workplace_type": workplace, "status": status,
                "salary_min": minimum, "salary_max": maximum, "deadline": deadline,
            }
            posting = create_posting(details, requirements)
        except ValueError as exc:
            flash(str(exc), "danger")
        except IntegrityError:
            flash("The posting could not be saved. Check the selected category and skills.", "danger")
        else:
            flash("Job published." if posting.status == "open" else "Draft saved.", "success")
            return redirect(url_for("company.dashboard"))
    return render_template("company/job_form.html", categories=categories, skills=skills,
                           proficiencies=PROFICIENCIES, today=today.isoformat())


@company_bp.post("/jobs/<int:job_id>/close")
@roles_required("recruiter")
def close_job(job_id):
    company_job(job_id)
    changed = company_model.close_posting(job_id)
    flash("Job closed." if changed else "This job is already closed or rejected.", "info")
    return redirect(url_for("company.dashboard"))


@company_bp.post("/jobs/<int:job_id>/delete")
@roles_required("recruiter")
def delete_job(job_id):
    job = company_job(job_id)
    result = delete_or_close_posting(job_id, request.form.get("confirm_delete") == "yes")
    if result is None:
        abort(404)
    if result == "retained":
        flash("This posting and its application history were retained. It is no longer open.", "info")
    elif result == "confirmation_required":
        return render_template("company/delete_job.html", job=job)
    else:
        flash(f'"{job.title}" deleted.', "success")
    return redirect(url_for("company.dashboard"))


@company_bp.get("/jobs/<int:job_id>/applicants")
@roles_required("recruiter")
def applicants(job_id):
    job = company_job(job_id)
    applications = company_model.list_job_applicants(job_id)
    return render_template("company/applicants.html", job=job, applications=applications)


@company_bp.route("/applications/<int:application_id>", methods=["GET", "POST"])
@roles_required("recruiter")
def applicant_detail(application_id):
    application = company_application(application_id)
    if request.method == "POST":
        try:
            next_status = request.form.get("status")
            if next_status == "hired":
                raise ValueError("Use Hire candidate and enter the employment start date.")
            update_application_status(
                application,
                next_status,
                current_user,
                text_field(request.form, "note", 500),
            )
            flash("Status updated.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("company.applicant_detail", application_id=application_id))
    params = {"user_id": application.applicant_id, "id": application_id, "resume_id": application.resume_id}
    candidate = company_model.find_candidate(params)
    skills = company_model.list_applicant_skills(params)
    experiences = company_model.list_applicant_experience(params)
    educations = company_model.list_applicant_education(params)
    resume = company_model.find_resume_title(params)
    history = company_model.list_review_history(params)
    available_statuses = sorted(TRANSITIONS.get(application.status, set()) - {"hired"})
    return render_template(
        "company/applicant_detail.html",
        application=application,
        candidate=candidate,
        skills=skills,
        experiences=experiences,
        educations=educations,
        resume=resume,
        history=history,
        interviews=list_application_interviews(params),
        interview_statuses=INTERVIEW_STATUSES,
        available_statuses=available_statuses,
        today=local_today().isoformat(),
    )


@company_bp.post("/applications/<int:application_id>/hire")
@roles_required("recruiter")
def hire_candidate(application_id):
    application = company_application(application_id)
    try:
        start_date = date_field(request.form, "start_date", required=True)
        update_application_status(
            application,
            "hired",
            current_user,
            text_field(request.form, "note", 500) or "Candidate hired",
            employment_start_date=start_date,
        )
        flash("Candidate hired and experience added to their profile.", "success")
    except ApplicationError as exc:
        flash(str(exc), "danger")
    except (KeyError, ValueError):
        flash("Enter a valid employment start date.", "danger")
    return redirect(url_for("company.applicant_detail", application_id=application.id))


@company_bp.get("/applications/<int:application_id>/resume")
@roles_required("recruiter")
def application_resume(application_id):
    application = company_application(application_id)
    resume = company_model.find_resume(application.resume_id)
    if resume is None:
        abort(404)
    return resume_file_response(resume)


@company_bp.post("/applications/<int:application_id>/interviews")
@roles_required("recruiter")
def schedule_interview(application_id):
    application = company_application(application_id)
    try:
        book_interview(application, current_user.id, request.form.get("scheduled_at"),
                       request.form.get("interview_type"),
                       text_field(request.form, "location_or_link", 500, required=True),
                       text_field(request.form, "notes", 4000))
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Interview scheduled.", "success")
    return redirect(url_for("company.applicant_detail", application_id=application.id))


@company_bp.post("/applications/<int:application_id>/interviews/<int:interview_id>/status")
@roles_required("recruiter")
def update_interview(application_id, interview_id):
    application = company_application(application_id)
    try:
        if not change_interview_status(application, interview_id, request.form.get("status")):
            abort(404)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Interview status updated.", "success")
    return redirect(url_for("company.applicant_detail", application_id=application_id))
