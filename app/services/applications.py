from types import SimpleNamespace

from app.clock import local_today
from app.database import write_transaction
from app.models import applications

TRANSITIONS = {
    "submitted": {"reviewing", "rejected", "withdrawn"},
    "reviewing": {"shortlisted", "interview", "rejected"},
    "shortlisted": {"interview", "offered", "rejected"},
    "interview": {"offered", "rejected"},
    "offered": {"hired", "rejected"},
    "hired": set(),
    "rejected": set(),
    "withdrawn": set(),
}


class ApplicationError(ValueError):
    pass


def submit_application(user, job_id, resume_id=None, cover_letter=None):
    with write_transaction():
        if not user.has_role("jobseeker"):
            raise ApplicationError("Only job seekers can apply.")
        job = applications.lock_posting_for_application(job_id)
        expired = job is not None and job.deadline is not None and job.deadline < local_today()
        if job is None or job.status != "open" or expired:
            if expired:
                raise ApplicationError("The application deadline has passed.")
            raise ApplicationError("This job is not open.")
        if applications.application_exists(job_id, user.id):
            raise ApplicationError("You have already applied to this job.")
        if resume_id and not applications.candidate_owns_resume(resume_id, user.id):
            raise ApplicationError("Choose one of your own CVs.")
        application = applications.insert_application(job_id, user.id, resume_id, cover_letter)
        if application is None:
            raise ApplicationError("You have already applied to this job.")
        applications.insert_initial_history(application.id, user.id)
    return SimpleNamespace(**application._asdict())


def update_application_status(
    application, new_status, actor, note=None, employment_start_date=None
):
    old_status = application.status
    if new_status not in TRANSITIONS.get(old_status, set()):
        raise ApplicationError(f"Invalid transition: {old_status} → {new_status}")
    with write_transaction():
        updated_id = applications.update_status(new_status, application.id, old_status)
        if updated_id is None:
            raise ApplicationError("The application status changed. Refresh and try again.")
        applications.insert_status_history(application.id, old_status, new_status, actor.id, note)
        job = applications.find_posting_context(application.job_id)
        title = "Application status updated"
        message = f"Your application for {job.title} is now {new_status}."
        if new_status == "hired":
            applications.insert_hired_experience({**job._asdict(), "user_id": application.applicant_id,
                   "start_date": employment_start_date or local_today()})
            title = "Congratulations — you were hired"
            message = f"You were hired by {job.company_name} as {job.title}."
        applications.insert_notification(
            application.applicant_id,
            title,
            message,
            f"/seeker/applications/{application.id}",
        )
    application.status = new_status
    return application
