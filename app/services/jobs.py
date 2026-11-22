from app.database import write_transaction
from app.models import companies


PROFICIENCIES = ("beginner", "intermediate", "advanced", "expert")
EMPLOYMENT_TYPES = ("full_time", "part_time", "internship", "contract")
WORKPLACE_TYPES = ("onsite", "hybrid", "remote")
POSTING_STATUSES = ("draft", "open", "closed", "rejected")


def create_posting(details, requirements):
    with write_transaction():
        posting = companies.insert_job(details)
        companies.insert_job_skills(posting.id, requirements)
    return posting


def delete_or_close_posting(job_id, confirmed):
    with write_transaction():
        posting = companies.lock_job(job_id)
        if posting is None:
            return None
        if companies.count_job_applications(job_id):
            if posting.status in ("open", "draft"):
                companies.set_job_closed(job_id)
            return "retained"
        if not confirmed:
            return "confirmation_required"
        companies.remove_job(job_id)
        return "deleted"
