from contextlib import contextmanager

from flask import current_app, g
import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import namedtuple_row


def get_db():
    if "postgres_connection" not in g:
        url = current_app.config["DATABASE_URL"]
        options = {"row_factory": namedtuple_row, "connect_timeout": 5}
        if current_app.config["ON_VERCEL"]:
            settings = conninfo_to_dict(url)
            options.update(sslmode="verify-full", sslrootcert=settings.get("sslrootcert", "system"),
                           prepare_threshold=None)
        elif "-pooler." in conninfo_to_dict(url).get("host", ""):
            options["prepare_threshold"] = None
        g.postgres_connection = psycopg.connect(url, **options)
    return g.postgres_connection


def close_db(error=None):
    connection = g.pop("postgres_connection", None)
    if connection is not None:
        connection.close()


@contextmanager
def write_transaction():
    connection = get_db()
    try:
        yield
        connection.commit()
    except Exception:
        if not connection.closed:
            try:
                connection.rollback()
            except psycopg.OperationalError:
                connection.close()
        raise
