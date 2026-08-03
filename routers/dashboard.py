from flask import Blueprint, abort, redirect, render_template, url_for

from utils import get_current_user, get_db_connection, login_required

dashboard_bp = Blueprint("dashboard", __name__)


def _can_access(role):
    user = get_current_user()
    return user and (user["role"] == role or user["role"] == "admin")


def _base_context(role):
    connection = get_db_connection()
    user = get_current_user()

    notifications = connection.execute(
        """
        SELECT message, created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user["id"],),
    ).fetchall()

    if role == "student":
        jobs = connection.execute(
            """
            SELECT jobs.id, jobs.title, jobs.company, jobs.description, jobs.created_at,
                   users.name AS posted_by_name
            FROM jobs
            JOIN users ON users.id = jobs.posted_by
            WHERE jobs.status = 'open'
            ORDER BY jobs.id DESC
            """
        ).fetchall()
        applications = connection.execute(
            """
            SELECT applications.job_id, applications.status, applications.applied_at,
                   jobs.title, jobs.company
            FROM applications
            JOIN jobs ON jobs.id = applications.job_id
            WHERE applications.user_id = ?
            ORDER BY applications.id DESC
            """,
            (user["id"],),
        ).fetchall()
        context = {"jobs": jobs, "applications": applications}
    elif role == "faculty":
        students = connection.execute(
            """
            SELECT id, name, email, approved, created_at
            FROM users
            WHERE role = 'student'
            ORDER BY id DESC
            """
        ).fetchall()
        jobs = connection.execute(
            "SELECT id, title, company, status, created_at FROM jobs ORDER BY id DESC"
        ).fetchall()
        context = {"students": students, "jobs": jobs}
    elif role == "tpo":
        jobs = connection.execute(
            """
            SELECT id, title, company, description, status, created_at
            FROM jobs
            WHERE posted_by = ?
            ORDER BY id DESC
            """,
            (user["id"],),
        ).fetchall()
        applications = connection.execute(
            """
            SELECT applications.id, applications.status, applications.applied_at,
                   jobs.title, jobs.company,
                   users.name AS student_name, users.email AS student_email
            FROM applications
            JOIN jobs ON jobs.id = applications.job_id
            JOIN users ON users.id = applications.user_id
            WHERE jobs.posted_by = ?
            ORDER BY applications.id DESC
            """,
            (user["id"],),
        ).fetchall()
        context = {"jobs": jobs, "applications": applications}
    else:
        pending_users = connection.execute(
            """
            SELECT id, name, email, role, approved, created_at
            FROM users
            WHERE approved = 0 AND role != 'admin'
            ORDER BY id DESC
            """
        ).fetchall()
        users = connection.execute(
            "SELECT id, name, email, role, approved, created_at FROM users ORDER BY id DESC"
        ).fetchall()
        jobs = connection.execute(
            """
            SELECT jobs.id, jobs.title, jobs.company, jobs.status, jobs.created_at,
                   users.name AS posted_by_name
            FROM jobs
            JOIN users ON users.id = jobs.posted_by
            ORDER BY jobs.id DESC
            """
        ).fetchall()
        context = {"pending_users": pending_users, "users": users, "jobs": jobs}

    connection.close()
    context["notifications"] = notifications
    context["current_user"] = user
    return context


@dashboard_bp.route("/dashboard")
@login_required
def role_redirect():
    current_user = get_current_user()
    return redirect(url_for("dashboard.role_dashboard", role=current_user["role"]))


@dashboard_bp.route("/dashboard/<role>")
@login_required
def role_dashboard(role):
    if role not in {"student", "faculty", "tpo", "admin"}:
        abort(404)
    if not _can_access(role):
        abort(403)

    context = _base_context(role)
    return render_template("dashboard.html", role=role, **context)
