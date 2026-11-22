from psycopg.rows import scalar_row
from app.database import get_db, write_transaction


def create_company(owner_id, details):
    with write_transaction():
        company_id = _insert_company(details)
        _assign_company_owner(company_id, owner_id)
        return company_id


def find_job(record_id):
    return get_db().execute("SELECT * FROM job_postings WHERE id = %(id)s", {"id": record_id}).fetchone()


def find_application(record_id):
    return get_db().execute("""
        SELECT a.*, j.company_id, j.title AS job_title
        FROM applications AS a JOIN job_postings AS j ON j.id = a.job_id
        WHERE a.id = %(id)s
    """, {"id": record_id}).fetchone()


def list_memberships(params):
    return get_db().execute("""
        SELECT s.*, c.name, c.industry, c.is_verified
        FROM company_staff AS s JOIN companies AS c ON c.id = s.company_id
        WHERE s.user_id = %(user_id)s ORDER BY c.name
    """, params).fetchall()


def list_staff_postings(params):
    return get_db().execute("""
        SELECT j.id, j.company_id, j.title, j.status, COUNT(a.id) AS application_count
        FROM job_postings AS j JOIN company_staff AS s ON s.company_id = j.company_id
        LEFT JOIN applications AS a ON a.job_id = j.id
        WHERE s.user_id = %(user_id)s GROUP BY j.id ORDER BY j.id
    """, params).fetchall()


def _insert_company(params):
    return get_db().cursor(row_factory=scalar_row).execute("""
        INSERT INTO companies (name, industry, description, website, city, country,
                               is_verified, created_at, updated_at)
        VALUES (%(name)s, %(industry)s, %(description)s, %(website)s, %(city)s, %(country)s,
                FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id
    """, params).fetchone()


def _assign_company_owner(company_id, user_id):
    return get_db().execute("""
        INSERT INTO company_staff (company_id, user_id, title, can_manage_company, joined_at)
        VALUES (%(company_id)s, %(user_id)s, 'Owner', TRUE, CURRENT_TIMESTAMP)
    """, {"company_id": company_id, "user_id": user_id})


def update_company(params):
    with write_transaction():
        return get_db().execute("""
            UPDATE companies SET name = %(name)s, industry = %(industry)s, description = %(description)s,
                                 website = %(website)s, city = %(city)s, country = %(country)s,
                                 updated_at = CURRENT_TIMESTAMP
            WHERE id = %(id)s
        """, params)


def find_company(record_id):
    return get_db().execute("SELECT * FROM companies WHERE id = %(id)s", {"id": record_id}).fetchone()


def insert_job(params):
    return get_db().execute("""
            INSERT INTO job_postings (company_id, category_id, created_by, title, description,
                requirements, location, employment_type, workplace_type, salary_min, salary_max,
                deadline, status, created_at, updated_at)
            SELECT c.id, %(category_id)s, %(created_by)s, %(title)s, %(description)s,
                %(requirements)s, %(location)s, %(employment_type)s, %(workplace_type)s, %(salary_min)s, %(salary_max)s,
                %(deadline)s, CASE WHEN c.is_verified THEN %(status)s ELSE 'draft' END,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM companies AS c WHERE c.id = %(company_id)s
            RETURNING id, status
    """, params).fetchone()


def insert_job_skills(job_id, requirements):
    if requirements:
        with get_db().cursor() as cursor:
            cursor.executemany("""
                INSERT INTO job_required_skills (job_id, skill_id, is_mandatory, minimum_proficiency)
                VALUES (%s, %s, %s, %s)
            """, [(job_id, *requirement) for requirement in requirements])


def close_posting(record_id):
    with write_transaction():
        return set_job_closed(record_id)


def set_job_closed(job_id):
    return get_db().execute("""
        UPDATE job_postings SET status = 'closed', updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND status IN ('open', 'draft')
    """, (job_id,)).rowcount


def lock_job(job_id):
    return get_db().execute("SELECT status FROM job_postings WHERE id = %s FOR UPDATE", (job_id,)).fetchone()


def count_job_applications(job_id):
    return get_db().cursor(row_factory=scalar_row).execute("""
        SELECT COUNT(*) FROM applications WHERE job_id = %s
    """, (job_id,)).fetchone()


def remove_job(job_id):
    get_db().execute("DELETE FROM job_postings WHERE id = %s", (job_id,))


def list_job_applicants(record_id):
    return get_db().execute("""
        SELECT a.*, u.first_name || ' ' || u.last_name AS full_name
        FROM applications AS a JOIN users AS u ON u.id = a.applicant_id
        WHERE a.job_id = %(id)s ORDER BY a.id
    """, {"id": record_id}).fetchall()


def find_candidate(params):
    return get_db().execute("""
        SELECT u.first_name || ' ' || u.last_name AS full_name, u.email, u.phone, p.*
        FROM users AS u LEFT JOIN jobseeker_profiles AS p ON p.user_id = u.id
        WHERE u.id = %(user_id)s
    """, params).fetchone()


def list_applicant_skills(params):
    return get_db().execute("""
        SELECT us.*, s.name AS skill_name FROM user_skills AS us JOIN skills AS s ON s.id = us.skill_id
        WHERE us.user_id = %(user_id)s ORDER BY s.name
    """, params).fetchall()


def list_applicant_experience(params):
    return get_db().execute("SELECT * FROM experiences WHERE user_id = %(user_id)s", params).fetchall()


def list_applicant_education(params):
    return get_db().execute("SELECT * FROM educations WHERE user_id = %(user_id)s", params).fetchall()


def find_resume_title(params):
    return get_db().execute("SELECT title FROM resumes WHERE id = %(resume_id)s", params).fetchone()


def list_review_history(params):
    return get_db().execute("""
        SELECT h.*, u.first_name || ' ' || u.last_name AS actor_name
        FROM application_status_history AS h LEFT JOIN users AS u ON u.id = h.changed_by
        WHERE h.application_id = %(id)s ORDER BY h.changed_at, h.id
    """, params).fetchall()


def find_resume(record_id):
    return get_db().execute("SELECT title, file_url FROM resumes WHERE id = %(id)s", {"id": record_id}).fetchone()


def insert_interview(record_id, user_id, scheduled_at, kind, location, notes):
    return get_db().execute("""
        INSERT INTO interviews (application_id, scheduled_by, scheduled_at, interview_type,
            location_or_link, notes, status, created_at, updated_at)
        VALUES (%(id)s, %(user_id)s, %(scheduled_at)s, %(type)s, %(location)s, %(notes)s, 'scheduled',
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, {"id": record_id, "user_id": user_id, "scheduled_at": scheduled_at, "type": kind, "location": location, "notes": notes})


def lock_interview(application_id, interview_id):
    return get_db().execute("""
        SELECT status, scheduled_at FROM interviews WHERE application_id = %s AND id = %s FOR UPDATE
    """, (application_id, interview_id)).fetchone()


def lock_application_for_interview(application_id):
    return get_db().execute("SELECT status FROM applications WHERE id = %s FOR UPDATE", (application_id,)).fetchone()


def update_interview_status(application_id, interview_id, status):
    get_db().execute("""
        UPDATE interviews SET status = %s, updated_at = CURRENT_TIMESTAMP
        WHERE application_id = %s AND id = %s
    """, (status, application_id, interview_id))


def find_membership(company_id, user_id, manage):
    return get_db().execute("""
        SELECT * FROM company_staff
        WHERE company_id = %(company_id)s AND user_id = %(user_id)s
          AND (NOT %(manage)s OR can_manage_company)
    """, {"company_id": company_id, "user_id": user_id, "manage": manage}).fetchone()
