from functools import wraps
from sqlite3 import connect

from flask import abort, g, redirect, session, url_for
from werkzeug.security import generate_password_hash

DATABASE = "database.db"
ADMIN_EMAIL = "admin@placement.com"
ADMIN_PASSWORD = "admin123"
ALLOWED_ROLES = {"student", "faculty", "tpo"}


def get_db_connection():
    connection = connect(DATABASE)
    connection.row_factory = lambda cursor, row: {
        column[0]: value for column, value in zip(cursor.description, row)
    }
    return connection


def _ensure_column(cursor, table_name, column_name, column_definition):
    existing_columns = {
        row[1] for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")


def init_db():
    connection = connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            description TEXT NOT NULL,
            posted_by INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (posted_by) REFERENCES users (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, job_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        )
        """
    )

    _ensure_column(cursor, "users", "approved", "approved INTEGER NOT NULL DEFAULT 0")
    _ensure_column(
        cursor,
        "users",
        "created_at",
        "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
    )

    admin_exists = cursor.execute(
        "SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)
    ).fetchone()
    if admin_exists is None:
        cursor.execute(
            """
            INSERT INTO users (name, email, password, role, approved)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Admin", ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD), "admin", 1),
        )

    connection.commit()
    connection.close()


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    cached_user = getattr(g, "current_user", None)
    if cached_user and cached_user["id"] == user_id:
        return cached_user

    connection = get_db_connection()
    user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    connection.close()
    g.current_user = user
    return user


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if get_current_user() is None:
            return redirect(url_for("auth.login"))
        return view_function(*args, **kwargs)

    return wrapped_view


def role_required(*allowed_roles):
    def decorator(view_function):
        @wraps(view_function)
        def wrapped_view(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return redirect(url_for("auth.login"))
            if user["role"] not in allowed_roles and user["role"] != "admin":
                abort(403)
            return view_function(*args, **kwargs)

        return wrapped_view

    return decorator


def add_notification(user_id, message):
    connection = get_db_connection()
    connection.execute(
        "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
        (user_id, message),
    )
    connection.commit()
    connection.close()
