from psycopg.rows import scalar_row
from app.database import get_db, write_transaction


def list_candidate_applications(user_id):
    return get_db().execute("""
        SELECT a.*, j.title AS job_title, c.name AS company_name
        FROM applications AS a
        JOIN job_postings AS j ON j.id = a.job_id
        JOIN companies AS c ON c.id = j.company_id
        WHERE a.applicant_id = %(user_id)s ORDER BY a.applied_at DESC
    """, {"user_id": user_id}).fetchall()


def dashboard_counts(user_id):
    return get_db().execute("""
        SELECT (SELECT COUNT(*) FROM user_skills WHERE user_id = %(user_id)s) AS skills,
               (SELECT COUNT(*) FROM notifications WHERE user_id = %(user_id)s AND NOT is_read)
                   AS unread_notifications
    """, {"user_id": user_id}).fetchone()


def update_account_name(params):
    return get_db().execute("""
        UPDATE users SET first_name = %(first_name)s, last_name = %(last_name)s, phone = %(phone)s,
                         updated_at = CURRENT_TIMESTAMP
        WHERE id = %(user_id)s
    """, params)


def upsert_profile(params):
    return get_db().execute("""
        INSERT INTO jobseeker_profiles (
            user_id, headline, bio, city, country, linkedin_url, portfolio_url, created_at, updated_at
        )
        VALUES (%(user_id)s, %(headline)s, %(bio)s, %(city)s, %(country)s, %(linkedin_url)s, %(portfolio_url)s,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO UPDATE
        SET headline = EXCLUDED.headline, bio = EXCLUDED.bio, city = EXCLUDED.city,
            country = EXCLUDED.country, linkedin_url = EXCLUDED.linkedin_url,
            portfolio_url = EXCLUDED.portfolio_url, updated_at = CURRENT_TIMESTAMP
    """, params)


def find_profile(params):
    return get_db().execute("""
        SELECT * FROM jobseeker_profiles WHERE user_id = %(user_id)s
    """, params).fetchone()


def list_education(params):
    return get_db().execute("""
        SELECT * FROM educations WHERE user_id = %(user_id)s ORDER BY id
    """, params).fetchall()


def list_experience(params):
    return get_db().execute("""
        SELECT * FROM experiences WHERE user_id = %(user_id)s ORDER BY id
    """, params).fetchall()


def list_resumes(params):
    return get_db().execute("""
        SELECT * FROM resumes WHERE user_id = %(user_id)s ORDER BY id
    """, params).fetchall()


def list_candidate_skills(params):
    return get_db().execute("""
        SELECT us.*, s.name AS skill_name FROM user_skills AS us
        JOIN skills AS s ON s.id = us.skill_id WHERE us.user_id = %(user_id)s
    """, params).fetchall()


def list_available_skills(params):
    return get_db().execute("""
        SELECT id, name FROM skills AS s
        WHERE NOT EXISTS (SELECT 1 FROM user_skills WHERE user_id = %(user_id)s AND skill_id = s.id)
        ORDER BY name
    """, params).fetchall()


def find_skill_for_candidate(params):
    return get_db().execute("""
        SELECT s.name, us.user_id IS NOT NULL AS already_added
        FROM skills AS s LEFT JOIN user_skills AS us ON us.skill_id = s.id AND us.user_id = %(user_id)s
        WHERE s.id = %(skill_id)s
    """, params).fetchone()


def insert_candidate_skill(params):
    with write_transaction():
        return get_db().execute("""
            INSERT INTO user_skills (user_id, skill_id, proficiency, years_experience)
            VALUES (%(user_id)s, %(skill_id)s, %(proficiency)s, %(years)s)
            ON CONFLICT (user_id, skill_id) DO NOTHING
        """, params)


def remove_candidate_skill(user_id, skill_id):
    with write_transaction():
        return get_db().execute("""
            DELETE FROM user_skills WHERE user_id = %(user_id)s AND skill_id = %(skill_id)s
        """, {"user_id": user_id, "skill_id": skill_id}).rowcount > 0


def insert_education(user_id, institution, degree, field, start, end):
    with write_transaction():
        return get_db().execute("""
            INSERT INTO educations (
                user_id, institution, degree, field_of_study, start_date, end_date, created_at, updated_at
            )
            VALUES (%(user_id)s, %(institution)s, %(degree)s, %(field)s, %(start)s, %(end)s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, {"user_id": user_id, "institution": institution, "degree": degree, "field": field, "start": start, "end": end})


def insert_experience(user_id, company_name, title, start, end):
    with write_transaction():
        return get_db().execute("""
            INSERT INTO experiences (user_id, company_name, title, start_date, end_date, created_at, updated_at)
            VALUES (%(user_id)s, %(company_name)s, %(title)s, %(start)s, %(end)s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, {"user_id": user_id, "company_name": company_name, "title": title, "start": start, "end": end})


def lock_resume_owner(params):
    return get_db().execute("SELECT id FROM users WHERE id = %(user_id)s FOR UPDATE", params)


def has_resumes(params):
    return get_db().cursor(row_factory=scalar_row).execute("""
        SELECT EXISTS (SELECT 1 FROM resumes WHERE user_id = %(user_id)s)
    """, params).fetchone()


def clear_primary_resume(params):
    return get_db().execute("""
        UPDATE resumes SET is_primary = FALSE, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %(user_id)s AND is_primary
    """, params)


def insert_resume(params):
    return get_db().execute("""
        INSERT INTO resumes (user_id, title, file_url, is_primary, created_at, updated_at)
        VALUES (%(user_id)s, %(title)s, %(file_url)s, %(primary)s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, params)


def find_owned_resume(record_id, user_id):
    return get_db().execute("""
        SELECT title, file_url FROM resumes WHERE id = %(id)s AND user_id = %(user_id)s
    """, {"id": record_id, "user_id": user_id}).fetchone()


def find_owned_resume_title(params):
    return get_db().cursor(row_factory=scalar_row).execute("""
        SELECT title FROM resumes WHERE id = %(id)s AND user_id = %(user_id)s
    """, params).fetchone()


def mark_primary_resume(params):
    return get_db().execute("""
        UPDATE resumes SET is_primary = (id = %(id)s), updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %(user_id)s AND is_primary <> (id = %(id)s)
    """, params)


def remove_owned_resume(params):
    return get_db().execute("""
        DELETE FROM resumes WHERE id = %(id)s AND user_id = %(user_id)s
        RETURNING file_url, is_primary
    """, params).fetchone()


def promote_first_resume(params):
    return get_db().execute("""
        UPDATE resumes SET is_primary = TRUE, updated_at = CURRENT_TIMESTAMP
        WHERE id = (SELECT id FROM resumes WHERE user_id = %(user_id)s ORDER BY id LIMIT 1)
    """, params)


def remove_bookmark(params):
    return get_db().cursor(row_factory=scalar_row).execute("""
        DELETE FROM saved_jobs
        WHERE user_id = %(user_id)s AND job_id = %(job_id)s
        RETURNING job_id
    """, params).fetchone()


def insert_bookmark(params):
    return get_db().execute("""
        INSERT INTO saved_jobs (user_id, job_id, saved_at)
        VALUES (%(user_id)s, %(job_id)s, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id, job_id) DO NOTHING
    """, params)


def find_owned_application(params):
    return get_db().execute("""
        SELECT a.*, j.title AS job_title, c.name AS company_name FROM applications AS a
        JOIN job_postings AS j ON j.id = a.job_id JOIN companies AS c ON c.id = j.company_id
        WHERE a.id = %(id)s AND a.applicant_id = %(user_id)s
    """, params).fetchone()


def list_application_history(params):
    return get_db().execute("""
        SELECT * FROM application_status_history WHERE application_id = %(id)s ORDER BY changed_at, id
    """, params).fetchall()


def list_application_interviews(params):
    return get_db().execute("""
        SELECT * FROM interviews WHERE application_id = %(id)s ORDER BY scheduled_at, id
    """, params).fetchall()


def list_bookmarks(user_id):
    return get_db().execute("""
        SELECT j.id, j.title, j.location, c.name AS company_name FROM saved_jobs AS s
        JOIN job_postings AS j ON j.id = s.job_id JOIN companies AS c ON c.id = j.company_id
        WHERE s.user_id = %(user_id)s AND c.is_verified AND j.status IN ('open', 'closed')
        ORDER BY s.saved_at DESC
    """, {"user_id": user_id}).fetchall()


def list_notifications(user_id):
    return get_db().execute("""
        SELECT n.id, n.title, n.message, n.is_read, n.created_at, a.id AS application_id
        FROM notifications AS n
        LEFT JOIN applications AS a ON n.link = '/seeker/applications/' || a.id AND a.applicant_id = n.user_id
        WHERE n.user_id = %s ORDER BY n.created_at DESC, n.id DESC
    """, (user_id,)).fetchall()


def mark_notification_read(user_id, notification_id):
    with write_transaction():
        return get_db().execute("""
            UPDATE notifications SET is_read = TRUE WHERE user_id = %s AND id = %s
        """, (user_id, notification_id)).rowcount > 0
