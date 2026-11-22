from app.database import write_transaction
from app.models import candidates as model
from app.services.resumes import BLOB_FILE_PREFIX, delete_resume_file


def update_profile(user_id, first_name, last_name, phone, details):
    with write_transaction():
        model.update_account_name({"user_id": user_id, "first_name": first_name, "last_name": last_name, "phone": phone})
        model.upsert_profile({**details, "user_id": user_id})


def save_resume(user_id, title, file_url, make_primary):
    params = {"user_id": user_id}
    with write_transaction():
        model.lock_resume_owner(params)
        make_primary = make_primary or not model.has_resumes(params)
        if make_primary:
            model.clear_primary_resume(params)
        model.insert_resume({**params, "title": title, "file_url": file_url, "primary": make_primary})


def choose_primary_resume(user_id, resume_id):
    params = {"user_id": user_id, "id": resume_id}
    with write_transaction():
        model.lock_resume_owner(params)
        title = model.find_owned_resume_title(params)
        if title is not None:
            model.mark_primary_resume(params)
        return title


def delete_resume(user_id, resume_id):
    params = {"user_id": user_id, "id": resume_id}
    with write_transaction():
        model.lock_resume_owner(params)
        resume = model.remove_owned_resume(params)
        if resume is not None and resume.is_primary:
            model.promote_first_resume(params)
        if resume is not None and resume.file_url.startswith(BLOB_FILE_PREFIX):
            delete_resume_file(resume.file_url)
        return resume


def toggle_bookmark(user_id, job_id):
    params = {"user_id": user_id, "job_id": job_id}
    with write_transaction():
        if model.remove_bookmark(params) is not None:
            return False
        model.insert_bookmark(params)
        return True
