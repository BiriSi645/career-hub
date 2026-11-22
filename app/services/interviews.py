from datetime import datetime, timezone

from app.database import write_transaction
from app.clock import ISTANBUL
from app.forms import public_http_url
from app.models import applications, companies


INTERVIEW_TYPES = ("video", "phone", "onsite")
INTERVIEW_STATUSES = ("scheduled", "completed", "cancelled")


def schedule_interview(application, recruiter_id, local_date_time, kind, location, notes):
    if kind not in INTERVIEW_TYPES:
        raise ValueError("Choose a valid interview type.")
    if kind == "video" and not public_http_url(location):
        raise ValueError("Enter an http:// or https:// meeting link for a video interview.")
    try:
        scheduled_at = datetime.strptime(local_date_time or "", "%Y-%m-%dT%H:%M").replace(tzinfo=ISTANBUL)
    except ValueError:
        raise ValueError("Enter a valid interview date and time.") from None
    if scheduled_at <= datetime.now(timezone.utc):
        raise ValueError("Choose an interview time in the future.")
    with write_transaction():
        current = companies.lock_application_for_interview(application.id)
        if current is None or current.status in {"hired", "rejected", "withdrawn"}:
            raise ValueError("Only an active application can have a new interview.")
        companies.insert_interview(application.id, recruiter_id, scheduled_at, kind, location, notes)
        applications.insert_notification(
            application.applicant_id,
            "Interview scheduled",
            f"An interview was scheduled for {application.job_title}.",
            f"/seeker/applications/{application.id}",
        )


def change_interview_status(application, interview_id, status):
    if status not in INTERVIEW_STATUSES:
        raise ValueError("Choose a valid interview status.")
    with write_transaction():
        interview = companies.lock_interview(application.id, interview_id)
        if interview is None:
            return False
        if status == "scheduled" and interview.scheduled_at <= datetime.now(timezone.utc):
            raise ValueError("A past interview cannot be marked scheduled.")
        if interview.status != status:
            companies.update_interview_status(application.id, interview_id, status)
            applications.insert_notification(
                application.applicant_id,
                "Interview updated",
                f"The interview for {application.job_title} is now {status}.",
                f"/seeker/applications/{application.id}",
            )
    return True
