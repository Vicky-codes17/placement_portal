from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from utils import ALLOWED_ROLES, get_db_connection

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def home():
    return render_template("index.html", page_title="Placement Portal")


@auth_bp.route("/register", methods=["GET", "POST"])
@auth_bp.route("/register/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "")

        if not full_name or not email or not password or not role:
            flash("Please fill in all fields.", "error")
        elif role not in ALLOWED_ROLES:
            flash("Please choose student, faculty, or TPO.", "error")
        else:
            connection = get_db_connection()
            existing_user = connection.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing_user:
                flash("A user already exists with this email.", "error")
            else:
                connection.execute(
                    """
                    INSERT INTO users (name, email, password, role, approved)
                    VALUES (?, ?, ?, ?, 0)
                    """,
                    (full_name, email, generate_password_hash(password), role),
                )
                connection.commit()
                connection.close()
                flash("Registration saved. Wait for admin approval.", "success")
                return redirect(url_for("auth.login"))
            connection.close()

    return render_template("register.html", page_title="Register")


@auth_bp.route("/register.html")
def register_html():
    return redirect(url_for("auth.register"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        connection = get_db_connection()
        user = connection.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        connection.close()

        if user is None or not check_password_hash(user["password"], password):
            flash("Invalid email or password.", "error")
        elif user["role"] != "admin" and not user["approved"]:
            flash("Your account is pending admin approval.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["user_role"] = user["role"]
            session["user_name"] = user["name"]
            flash("Login successful.", "success")
            return redirect(url_for("dashboard.role_redirect"))

    return render_template("login.html", page_title="Login")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.home"))
