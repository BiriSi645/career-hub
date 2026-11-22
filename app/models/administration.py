from psycopg import sql
from psycopg.rows import dict_row, scalar_row
from app.database import get_db, write_transaction


BROWSER_TABLES = (
    "applications", "application_status_history", "companies", "company_staff", "educations",
    "experiences", "interviews", "job_categories", "job_postings", "job_required_skills",
    "jobseeker_profiles", "notifications", "resumes", "roles", "saved_jobs", "skills",
    "user_roles", "user_skills", "users",
)
PRIVATE_COLUMNS = {"password_hash", "email", "phone", "file_url", "cover_letter", "bio", "message", "notes"}


def search_employments(search, status, today):
    return _employment_rows("""
        (%(all_statuses)s OR (%(current)s AND (e.end_date IS NULL OR e.end_date >= %(today)s))
          OR (%(past)s AND e.end_date < %(today)s))
        AND (%(skip_search)s OR u.first_name ILIKE %(pattern)s OR u.last_name ILIKE %(pattern)s
             OR u.email ILIKE %(pattern)s OR e.company_name ILIKE %(pattern)s
             OR e.title ILIKE %(pattern)s OR e.location ILIKE %(pattern)s)
    """, {"all_statuses": status == "all", "current": status == "current",
          "past": status == "past", "today": today, "skip_search": not search,
          "pattern": f"%{search}%"})


def company_employments(company_id, company_name):
    return _employment_rows("""
        e.company_id = %(id)s OR (e.company_id IS NULL AND lower(trim(e.company_name)) = %(name)s)
    """, {"id": company_id, "name": company_name.strip().lower()})


def _employment_rows(condition, params):
    return get_db().execute(f"""
        SELECT e.*, u.first_name || ' ' || u.last_name AS full_name, u.email, u.phone,
               p.headline, p.city, p.country,
               ARRAY(SELECT s.name FROM user_skills AS us JOIN skills AS s ON s.id = us.skill_id
                     WHERE us.user_id = u.id ORDER BY s.name) AS skill_names
        FROM experiences AS e JOIN users AS u ON u.id = e.user_id
        LEFT JOIN jobseeker_profiles AS p ON p.user_id = u.id
        WHERE {condition}
        ORDER BY e.end_date NULLS FIRST, e.start_date DESC, u.first_name
    """, params).fetchall()


def dashboard_counts(today):
    return get_db().cursor(row_factory=dict_row).execute("""
        SELECT (SELECT COUNT(*) FROM users) AS users,
               (SELECT COUNT(*) FROM companies) AS companies,
               (SELECT COUNT(*) FROM job_postings) AS jobs,
               (SELECT COUNT(*) FROM applications) AS applications,
               (SELECT COUNT(DISTINCT user_id) FROM experiences
                WHERE end_date IS NULL OR end_date >= %(today)s) AS employees
    """, {"today": today}).fetchone()


def category_counts():
    return get_db().execute("""
        SELECT c.name, COUNT(j.id) FROM job_categories AS c
        LEFT JOIN job_postings AS j ON j.category_id = c.id GROUP BY c.id ORDER BY c.name
    """).fetchall()


def employment_summary(today):
    return get_db().execute("""
        SELECT COUNT(DISTINCT user_id) FILTER (WHERE end_date IS NULL OR end_date >= %(today)s) AS people,
               COUNT(*) FILTER (WHERE end_date IS NULL OR end_date >= %(today)s) AS positions,
               COUNT(DISTINCT company_name) FILTER (WHERE end_date IS NULL OR end_date >= %(today)s) AS companies,
               COUNT(*) AS history
        FROM experiences
    """, {"today": today}).fetchone()


def list_table_names():
    return get_db().cursor(row_factory=scalar_row).execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE' AND table_name = ANY(%s)
        ORDER BY table_name
    """, (list(BROWSER_TABLES),)).fetchall()


def count_table_rows(table_name):
    if table_name not in BROWSER_TABLES:
        raise ValueError("Table is not available in the database browser.")
    return get_db().cursor(row_factory=scalar_row).execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier("public", table_name))).fetchone()


def list_table_columns(table):
    if table not in BROWSER_TABLES:
        raise ValueError("Table is not available in the database browser.")
    return get_db().execute("""
        SELECT column_name AS name, data_type AS type, is_nullable = 'YES' AS nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name <> ALL(%s)
        ORDER BY ordinal_position
    """, (table, sorted(PRIVATE_COLUMNS))).fetchall()


def list_table_rows(table_name, columns):
    if table_name not in BROWSER_TABLES or any(column.name in PRIVATE_COLUMNS for column in columns):
        raise ValueError("These fields are not available in the database browser.")
    query = sql.SQL("SELECT {} FROM {} LIMIT 100").format(
        sql.SQL(", ").join(sql.Identifier(column.name) for column in columns),
        sql.Identifier("public", table_name),
    )
    return get_db().cursor(row_factory=dict_row).execute(query).fetchall()


def toggle_user_active(record_id):
    return get_db().cursor(row_factory=scalar_row).execute("""
            UPDATE users SET is_active_account = NOT is_active_account, updated_at = CURRENT_TIMESTAMP
            WHERE id = %(id)s RETURNING id
    """, {"id": record_id}).fetchone()


def lock_admin_changes():
    get_db().execute("SELECT pg_advisory_xact_lock(708192361)")


def administrator_account(user_id):
    return get_db().execute("""
        SELECT u.is_active_account, EXISTS (
            SELECT 1 FROM user_roles AS ur JOIN roles AS r ON r.id = ur.role_id
            WHERE ur.user_id = u.id AND r.name = 'admin'
        ) AS is_admin
        FROM users AS u WHERE u.id = %s
    """, (user_id,)).fetchone()


def list_users():
    return get_db().execute("""
        SELECT u.id, u.first_name || ' ' || u.last_name AS full_name, u.email,
               u.is_active_account AS is_active,
               string_agg(r.name, ', ' ORDER BY r.name) AS role_names
        FROM users AS u LEFT JOIN user_roles AS ur ON ur.user_id = u.id
        LEFT JOIN roles AS r ON r.id = ur.role_id GROUP BY u.id ORDER BY u.created_at DESC
    """).fetchall()


def list_roles():
    return get_db().execute("SELECT id, name FROM roles ORDER BY id").fetchall()


def find_role_assignment(params):
    return get_db().execute("""
        SELECT r.name,
               EXISTS (SELECT 1 FROM user_roles WHERE user_id = %(user_id)s AND role_id = r.id) AS assigned,
               (SELECT COUNT(*) FROM user_roles WHERE user_id = %(user_id)s) AS role_count
        FROM roles AS r CROSS JOIN users AS u
        WHERE r.id = %(role_id)s AND u.id = %(user_id)s
    """, params).fetchone()


def insert_role_assignment(params):
    get_db().execute("""
            INSERT INTO user_roles (user_id, role_id, assigned_at)
            VALUES (%(user_id)s, %(role_id)s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, role_id) DO NOTHING
    """, params)


def count_active_admins():
    return get_db().cursor(row_factory=scalar_row).execute("""
        SELECT COUNT(*) FROM users AS u JOIN user_roles AS ur ON ur.user_id = u.id
        JOIN roles AS r ON r.id = ur.role_id WHERE r.name = 'admin' AND u.is_active_account
    """).fetchone()


def remove_role_assignment(params):
    get_db().execute("""
            DELETE FROM user_roles WHERE user_id = %(user_id)s AND role_id = %(role_id)s
    """, params)


def list_companies():
    return get_db().execute("""
        SELECT * FROM companies ORDER BY name
    """).fetchall()


def count_employees_by_company(today):
    return get_db().execute("""
        SELECT company_id, COUNT(DISTINCT user_id) FROM experiences
        WHERE company_id IS NOT NULL AND (end_date IS NULL OR end_date >= %(today)s)
        GROUP BY company_id
    """, {"today": today}).fetchall()


def find_company_overview(params):
    return get_db().execute("""
        SELECT c.*,
               (SELECT COUNT(*) FROM job_postings WHERE company_id = c.id) AS posting_count,
               (SELECT COUNT(*) FROM applications AS a JOIN job_postings AS j ON j.id = a.job_id
                WHERE j.company_id = c.id) AS application_count
        FROM companies AS c WHERE c.id = %(id)s
    """, params).fetchone()


def list_company_staff(params):
    return get_db().execute("""
        SELECT s.*, u.first_name || ' ' || u.last_name AS full_name, u.email
        FROM company_staff AS s JOIN users AS u ON u.id = s.user_id
        WHERE s.company_id = %(id)s ORDER BY s.id
    """, params).fetchall()


def toggle_company_verified(record_id):
    with write_transaction():
        return get_db().cursor(row_factory=scalar_row).execute("""
            UPDATE companies SET is_verified = NOT is_verified, updated_at = CURRENT_TIMESTAMP
            WHERE id = %(id)s RETURNING id
        """, {"id": record_id}).fetchone()


def list_postings():
    return get_db().execute("""
        SELECT j.*, c.name AS company_name FROM job_postings AS j
        JOIN companies AS c ON c.id = j.company_id ORDER BY j.created_at DESC
    """).fetchall()


def update_posting_status(record_id, status, today):
    with write_transaction():
        return get_db().cursor(row_factory=scalar_row).execute("""
            UPDATE job_postings AS j SET status = CAST(%(status)s AS varchar), updated_at = CURRENT_TIMESTAMP
            FROM companies AS c
            WHERE j.id = %(id)s AND c.id = j.company_id
              AND (CAST(%(status)s AS varchar) <> 'open'
                   OR (c.is_verified AND (j.deadline IS NULL OR j.deadline >= %(today)s)))
            RETURNING j.id
        """, {"id": record_id, "status": status, "today": today}).fetchone()


def catalog_name_exists(table, name):
    return get_db().cursor(row_factory=scalar_row).execute(sql.SQL("""
        SELECT EXISTS (SELECT 1 FROM {} WHERE lower(name) = lower(%s))
    """).format(sql.Identifier(table)), (name,)).fetchone()


def insert_catalog_item(table, name, detail):
    field = "description" if table == "job_categories" else "category"
    with write_transaction():
        statement = sql.SQL("INSERT INTO {} (name, {}) VALUES (%s, %s)").format(sql.Identifier(table), sql.Identifier(field))
        get_db().execute(statement, (name, detail))


def list_catalog_categories():
    return get_db().execute("SELECT id, name, description FROM job_categories ORDER BY name").fetchall()


def find_catalog_id(table, record_id):
    query = sql.SQL("SELECT id FROM {} WHERE id = %s").format(sql.Identifier(table))
    return get_db().cursor(row_factory=scalar_row).execute(query, (record_id,)).fetchone()


def catalog_name_used_by_another(table, params):
    query = sql.SQL("""
        SELECT EXISTS (SELECT 1 FROM {} WHERE lower(name) = lower(%(name)s) AND id <> %(id)s)
    """).format(sql.Identifier(table))
    return get_db().cursor(row_factory=scalar_row).execute(query, params).fetchone()


def update_catalog_name(table, params):
    field = "description" if table == "job_categories" else "category"
    query = sql.SQL("""
        UPDATE {} SET name = %(name)s, {} = CASE WHEN %(set_detail)s THEN %(detail)s ELSE {} END
        WHERE id = %(id)s
    """).format(sql.Identifier(table), sql.Identifier(field), sql.Identifier(field))
    with write_transaction():
        get_db().execute(query, params)


def find_catalog_name(table, params):
    query = sql.SQL("SELECT name FROM {} WHERE id = %(id)s").format(sql.Identifier(table))
    return get_db().cursor(row_factory=scalar_row).execute(query, params).fetchone()


def category_has_postings(params):
    return get_db().cursor(row_factory=scalar_row).execute("""
        SELECT EXISTS (SELECT 1 FROM job_postings WHERE category_id = %(id)s)
    """, params).fetchone()


def remove_catalog_item(table, params):
    with write_transaction():
        get_db().execute(sql.SQL("DELETE FROM {} WHERE id = %(id)s").format(sql.Identifier(table)), params)
