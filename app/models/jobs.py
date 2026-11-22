from psycopg.rows import scalar_row
from app.database import get_db


def latest_postings(today):
    return get_db().execute("""
        SELECT j.id, j.title, j.location, j.employment_type, c.name AS company_name
        FROM job_postings AS j
        JOIN companies AS c ON c.id = j.company_id
        WHERE j.status = 'open' AND c.is_verified AND (j.deadline IS NULL OR j.deadline >= %s)
        ORDER BY j.created_at DESC
        LIMIT 6
    """, (today,)).fetchall()


def search_postings(search, category_id, employment_type, today, *, filter_category=False):
    return get_db().execute("""
        SELECT j.id, j.title, j.location, j.description, j.workplace_type,
               c.name AS company_name
        FROM job_postings AS j
        JOIN companies AS c ON c.id = j.company_id
        WHERE j.status = 'open' AND c.is_verified AND (j.deadline IS NULL OR j.deadline >= %(today)s)
          AND (%(skip_search)s OR j.title ILIKE %(pattern)s OR c.name ILIKE %(pattern)s
               OR j.description ILIKE %(pattern)s)
          AND (%(skip_category)s OR j.category_id = %(category_id)s)
          AND (%(skip_type)s OR j.employment_type = %(employment_type)s)
        ORDER BY j.created_at DESC
    """, {
        "today": today,
        "skip_search": not search,
        "pattern": f"%{search}%",
        "skip_category": not filter_category,
        "category_id": category_id,
        "skip_type": not employment_type,
        "employment_type": employment_type,
    }).fetchall()


def list_categories():
    return get_db().execute("SELECT id, name FROM job_categories ORDER BY name").fetchall()


def find_public_posting(record_id, today):
    return get_db().execute("""
        SELECT j.*, c.name AS company_name,
               COALESCE(j.deadline < %(today)s, FALSE) AS deadline_has_passed,
               j.status = 'open' AND (j.deadline IS NULL OR j.deadline >= %(today)s)
                   AS is_accepting_applications
        FROM job_postings AS j JOIN companies AS c ON c.id = j.company_id
        WHERE j.id = %(id)s AND c.is_verified AND j.status IN ('open', 'closed')
    """, {"id": record_id, "today": today}).fetchone()


def homepage_counts(today):
    return get_db().execute("""
        SELECT COUNT(*) AS open_roles, COUNT(DISTINCT j.company_id) AS companies,
               COUNT(DISTINCT j.category_id) AS categories
        FROM job_postings AS j JOIN companies AS c ON c.id = j.company_id
        WHERE j.status = 'open' AND c.is_verified AND (j.deadline IS NULL OR j.deadline >= %s)
    """, (today,)).fetchone()


def required_skills(job_id):
    return get_db().execute("""
        SELECT s.name, r.is_mandatory, r.minimum_proficiency
        FROM job_required_skills AS r JOIN skills AS s ON s.id = r.skill_id
        WHERE r.job_id = %s ORDER BY r.is_mandatory DESC, s.name
    """, (job_id,)).fetchall()


def skill_catalog():
    return get_db().execute("SELECT id, name, category FROM skills ORDER BY name").fetchall()


def is_posting_saved(user_id, job_id):
    return get_db().cursor(row_factory=scalar_row).execute("""
        SELECT EXISTS (SELECT 1 FROM saved_jobs WHERE user_id = %(user_id)s AND job_id = %(job_id)s)
    """, {"user_id": user_id, "job_id": job_id}).fetchone()


def list_resume_choices(user_id):
    return get_db().execute("""
        SELECT id, title, is_primary FROM resumes WHERE user_id = %(user_id)s ORDER BY id
    """, {"user_id": user_id}).fetchall()
