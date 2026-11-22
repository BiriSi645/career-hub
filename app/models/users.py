from flask_login import UserMixin
from psycopg.rows import scalar_row
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import get_db, write_transaction


class SessionUser(UserMixin):
    def __init__(self, row, role_names):
        self.id = row.id
        self.first_name = row.first_name
        self.last_name = row.last_name
        self.phone = row.phone
        self.full_name = f"{row.first_name} {row.last_name}"
        self.is_active_account = row.is_active_account
        self.password_hash = row.password_hash
        self.role_names = role_names

    def has_role(self, name):
        return name in self.role_names

    @property
    def is_active(self):
        return self.is_active_account

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


def get_user(user_id):
    row = get_db().execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
    return _session_user(row)


def find_user_by_email(email):
    row = get_db().execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()
    return _session_user(row)


def _session_user(row):
    if row is None:
        return None
    with get_db().cursor(row_factory=scalar_row) as cursor:
        roles = cursor.execute("""
            SELECT r.name FROM roles AS r JOIN user_roles AS ur ON ur.role_id = r.id
            WHERE ur.user_id = %s
        """, (row.id,)).fetchall()
    return SessionUser(row, roles)


def create_account(email, password, first_name, last_name, role_name):
    password_hash = generate_password_hash(password)
    with write_transaction():
        account = _insert_account(email, password_hash, first_name, last_name, role_name)
    if account is None:
        return None
    return SessionUser(account, [role_name])


def create_first_admin(email, password, first_name, last_name):
    password_hash = generate_password_hash(password)
    with write_transaction():
        connection = get_db()
        connection.execute("SELECT pg_advisory_xact_lock(708192361)")
        existing = connection.execute("""
            SELECT EXISTS (SELECT 1 FROM user_roles AS ur
                           JOIN roles AS r ON r.id = ur.role_id WHERE r.name = 'admin')
        """).fetchone()[0]
        if existing:
            raise ValueError("An administrator already exists. Use the existing admin account to manage roles.")
        if _insert_account(email, password_hash, first_name, last_name, "admin") is None:
            raise ValueError("That email is already registered. Choose a new administrator email.")


def _insert_account(email, password_hash, first_name, last_name, role_name):
    connection = get_db()
    account = connection.execute("""
        INSERT INTO users (email, password_hash, first_name, last_name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (email) DO NOTHING
        RETURNING *
    """, (email, password_hash, first_name, last_name)).fetchone()
    if account is None:
        return None
    connection.execute("INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (role_name,))
    connection.execute("""
        INSERT INTO user_roles (user_id, role_id)
        SELECT %s, id FROM roles WHERE name = %s
    """, (account.id, role_name))
    if role_name == "jobseeker":
        connection.execute("INSERT INTO jobseeker_profiles (user_id) VALUES (%s)", (account.id,))
    return account
