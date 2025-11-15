import click
import json
from flask import Flask, render_template
from .extensions import db, login_manager
from .models import User


def create_app(config_object="config.Config"):
    app = Flask(__name__, instance_relative_config=True, static_folder="static", template_folder="templates")
    app.config.from_object(config_object)

    # init extensions
    db.init_app(app)
    login_manager.init_app(app)

    # jinja filters
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Convert JSON string to Python object"""
        if value is None:
            return []
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return []
    
    @app.template_filter('chr_uppercase')
    def chr_uppercase_filter(value):
        """Convert number to uppercase letter (0=A, 1=B, etc.)"""
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        if isinstance(value, int) and 0 <= value < 26:
            return alphabet[value]
        return str(value)

    # blueprints
    from .auth.routes import auth_bp
    from .main.routes import main_bp
    from .profesor import profesor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(profesor_bp)

    # create tables on first request
    @app.before_request
    def _create_tables():  # pragma: no cover
        db.create_all()

    # error handlers
    @app.errorhandler(403)
    def forbidden(_):
        return render_template("403.html"), 403

    register_cli(app)
    return app


def register_cli(app: Flask):
    @app.cli.command("create-user")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--role", type=click.Choice(["admin", "profesor", "estudiante"]), prompt=True)
    def create_user(username, email, password, role):
        """Create a user with the given role."""
        exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if exists:
            click.secho("Usuario o email ya existe", fg="red")
            raise SystemExit(1)
        u = User(username=username, email=email, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        click.secho(f"Usuario {username} creado con rol {role}", fg="green")
