from psycopg.rows import scalar_row
from app.database import get_db


def lock_posting_for_application(record_id):
    return get_db().execute("""
        SELECT j.status, j.deadline FROM job_postings AS j
        JOIN companies AS c ON c.id = j.company_id
        WHERE j.id = %(id)s AND c.is_verified FOR SHARE OF j, c
    """, {"id": record_id}).fetchone()


def application_exists(job_id, user_id):
    return get_db().cursor(row_factory=scalar_row).execute("""
        SELECT EXISTS (
            SELECT 1 FROM applications WHERE job_id = %(job_id)s AND applicant_id = %(user_id)s
        )
    """, {"job_id": job_id, "user_id": user_id}).fetchone()


def candidate_owns_resume(record_id, user_id):
    return get_db().execute("""
        SELECT id FROM resumes WHERE id = %s AND user_id = %s FOR KEY SHARE
    """, (record_id, user_id)).fetchone() is not None


def insert_application(job_id, applicant_id, resume_id, cover_letter):
    return get_db().execute("""
        INSERT INTO applications (
            job_id, applicant_id, resume_id, cover_letter, status,
            applied_at, created_at, updated_at
        )
        VALUES (
            %(job_id)s, %(applicant_id)s, %(resume_id)s, %(cover_letter)s, 'submitted',
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        ON CONFLICT (job_id, applicant_id) DO NOTHING
        RETURNING *
    """, {"job_id": job_id, "applicant_id": applicant_id, "resume_id": resume_id, "cover_letter": cover_letter}).fetchone()


def insert_initial_history(application_id, user_id):
    return get_db().execute("""
        INSERT INTO application_status_history (
            application_id, new_status, changed_by, note, changed_at
        )
        VALUES (%(application_id)s, 'submitted', %(user_id)s, 'Application submitted', CURRENT_TIMESTAMP)
    """, {"application_id": application_id, "user_id": user_id})


def update_status(new_status, application_id, old_status):
    return get_db().cursor(row_factory=scalar_row).execute("""
        UPDATE applications
        SET status = %(new_status)s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %(application_id)s AND status = %(old_status)s
        RETURNING id
    """, {"new_status": new_status, "application_id": application_id, "old_status": old_status}).fetchone()


def insert_status_history(application_id, old_status, new_status, actor_id, note):
    return get_db().execute("""
        INSERT INTO application_status_history (
            application_id, old_status, new_status, changed_by, note, changed_at
        )
        VALUES (%(application_id)s, %(old_status)s, %(new_status)s, %(actor_id)s, %(note)s, CURRENT_TIMESTAMP)
    """, {"application_id": application_id, "old_status": old_status, "new_status": new_status, "actor_id": actor_id, "note": note})


def find_posting_context(job_id):
    return get_db().execute("""
        SELECT j.company_id, j.title, j.location, c.name AS company_name
        FROM job_postings AS j JOIN companies AS c ON c.id = j.company_id
        WHERE j.id = %(job_id)s
    """, {"job_id": job_id}).fetchone()


def insert_hired_experience(params):
    return get_db().execute("""
        INSERT INTO experiences (
            user_id, company_id, company_name, title, location, start_date,
            description, created_at, updated_at
        )
        SELECT %(user_id)s, %(company_id)s, CAST(%(company_name)s AS varchar), CAST(%(title)s AS varchar),
               %(location)s, %(start_date)s,
               'Hired through Career Hub.', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM experiences
            WHERE user_id = %(user_id)s AND company_name = %(company_name)s
              AND title = %(title)s AND start_date = %(start_date)s
        )
    """, params)


def insert_notification(user_id, title, message, link):
    return get_db().execute("""
        INSERT INTO notifications (user_id, title, message, link, is_read, created_at)
        VALUES (%(user_id)s, %(title)s, %(message)s, %(link)s, FALSE, CURRENT_TIMESTAMP)
    """, {"user_id": user_id, "title": title, "message": message, "link": link})
