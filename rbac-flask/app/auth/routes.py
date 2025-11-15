from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from ..extensions import db
from ..models import User

auth_bp = Blueprint("auth", __name__, url_prefix="")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        username_or_email = request.form.get("username").strip()
        password = request.form.get("password")
        user = (
            User.query.filter((User.username == username_or_email) | (User.email == username_or_email))
            .first()
        )
        if user and user.check_password(password):
            login_user(user)
            flash("Bienvenido/a", "success")
            # redirigir según rol
            if user.role == "admin":
                return redirect(url_for("main.dashboard_admin"))
            elif user.role == "profesor":
                return redirect(url_for("main.dashboard_profesor"))
            else:
                return redirect(url_for("main.dashboard_estudiante"))
        flash("Credenciales inválidas", "danger")
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        role = request.form.get("role", "estudiante").strip()

        # Validar rol permitido
        if role not in ("estudiante", "profesor"):
            flash("Rol no válido. Selecciona estudiante o profesor.", "warning")
            return render_template("register.html")

        if not username or not email or not password:
            flash("Todos los campos son obligatorios", "warning")
            return render_template("register.html")

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Usuario o email ya existe", "warning")
            return render_template("register.html")

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f"Registro exitoso como {role}. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada", "info")
    return redirect(url_for("auth.login"))
