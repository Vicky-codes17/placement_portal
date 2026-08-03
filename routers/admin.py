from flask import Blueprint, abort, flash, redirect, url_for

from utils import add_notification, get_current_user, get_db_connection, login_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/approve/<int:user_id>", methods=["POST"])
@login_required
def approve_user(user_id):
    current_user = get_current_user()
    if current_user["role"] != "admin":
        abort(403)

    connection = get_db_connection()
    user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if user is None or user["role"] == "admin":
        connection.close()
        abort(404)

    if user["approved"] == 0:
        connection.execute("UPDATE users SET approved = 1 WHERE id = ?", (user_id,))
        connection.commit()
        connection.close()
        add_notification(user_id, "Your account has been approved by the admin.")
        flash("User approved and notification sent.", "success")
    else:
        connection.close()
        flash("User was already approved.", "info")

    return redirect(url_for("dashboard.role_dashboard", role="admin"))
