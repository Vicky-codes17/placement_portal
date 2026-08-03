from flask import Blueprint, flash, redirect, request, url_for

from utils import get_current_user, get_db_connection, login_required

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/jobs/post", methods=["POST"])
@login_required
def post_job():
    current_user = get_current_user()
    if current_user["role"] not in {"tpo", "admin"}:
        flash("Only TPO or admin can post jobs.", "error")
        return redirect(url_for("dashboard.role_dashboard", role=current_user["role"]))

    title = request.form.get("title", "").strip()
    company = request.form.get("company", "").strip()
    description = request.form.get("description", "").strip()

    if not title or not company or not description:
        flash("Please fill in all job fields.", "error")
        return redirect(url_for("dashboard.role_dashboard", role=current_user["role"]))

    connection = get_db_connection()
    connection.execute(
        """
        INSERT INTO jobs (title, company, description, posted_by, status)
        VALUES (?, ?, ?, ?, 'open')
        """,
        (title, company, description, current_user["id"]),
    )
    connection.commit()
    connection.close()

    flash("Job posted successfully.", "success")
    return redirect(url_for("dashboard.role_dashboard", role=current_user["role"]))


@jobs_bp.route("/jobs/<int:job_id>/apply", methods=["POST"])
@login_required
def apply_for_job(job_id):
    current_user = get_current_user()
    if current_user["role"] != "student":
        flash("Only students can apply for jobs.", "error")
        return redirect(url_for("dashboard.role_dashboard", role=current_user["role"]))

    connection = get_db_connection()
    job = connection.execute(
        "SELECT id FROM jobs WHERE id = ? AND status = 'open'", (job_id,)
    ).fetchone()
    if job is None:
        connection.close()
        flash("Job not found or closed.", "error")
        return redirect(url_for("dashboard.role_dashboard", role="student"))

    existing = connection.execute(
        "SELECT id FROM applications WHERE user_id = ? AND job_id = ?",
        (current_user["id"], job_id),
    ).fetchone()
    if existing:
        connection.close()
        flash("You already applied for this job.", "info")
        return redirect(url_for("dashboard.role_dashboard", role="student"))

    connection.execute(
        "INSERT INTO applications (user_id, job_id, status) VALUES (?, ?, 'pending')",
        (current_user["id"], job_id),
    )
    connection.commit()
    connection.close()

    flash("Application submitted successfully.", "success")
    return redirect(url_for("dashboard.role_dashboard", role="student"))
