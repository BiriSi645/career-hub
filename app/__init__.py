import click
from email_validator import validate_email
from flask import Flask
from psycopg import OperationalError
from config import BASE_DIR, Config
from .database import close_db
from .extensions import csrf, login_manager


def create_app(config_object=Config):
    app = Flask(__name__, static_folder=str(BASE_DIR / "public" / "static"), static_url_path="/static")
    app.config.from_object(config_object)
    app.teardown_appcontext(close_db)
    login_manager.init_app(app)
    csrf.init_app(app)

    @app.errorhandler(OperationalError)
    def database_unavailable(error):
        app.logger.warning("PostgreSQL operation unavailable (%s)", type(error).__name__)
        return "The database is temporarily unavailable. Please try again shortly.", 503, {"Retry-After": "5"}
    from .clock import local_time
    from .forms import public_http_url

    app.add_template_filter(local_time)
    app.add_template_filter(public_http_url)

    from .models.users import get_user
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.seeker import seeker_bp
    from .routes.company import company_bp
    from .routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(seeker_bp, url_prefix="/seeker")
    app.register_blueprint(company_bp, url_prefix="/company")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @login_manager.user_loader
    def load_user(user_id):
        user = get_user(int(user_id))
        return user if user and user.is_active else None

    @app.cli.group("db")
    def database_commands():
        """Manage the PostgreSQL schema."""

    @database_commands.command("upgrade")
    def database_upgrade():
        from .schema import upgrade_database

        upgrade_database()
        print("Career Hub database is up to date.")

    @app.cli.command("seed")
    def seed_command():
        from .seed import seed_database

        seed_database()
        print("Career Hub demo data seeded.")

    @app.cli.command("seed-catalog")
    def seed_catalog_command():
        """Insert the default roles, job categories, and skills."""
        from .database import write_transaction
        from .seed import seed_catalog

        with write_transaction():
            seed_catalog()
        click.echo("Career Hub catalog is ready.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--first-name", prompt=True)
    @click.option("--last-name", prompt=True)
    @click.password_option()
    def create_admin_command(email, first_name, last_name, password):
        """Create the first administrator in an initialized database."""
        from .forms import text_field
        from .models.users import create_first_admin

        try:
            email = validate_email(email, check_deliverability=False).normalized.lower()
            first_name = text_field({"first_name": first_name}, "first_name", 80, required=True)
            last_name = text_field({"last_name": last_name}, "last_name", 80, required=True)
            if len(email) > 255 or not 12 <= len(password) <= 128:
                raise ValueError("Use a valid email and a password between 12 and 128 characters.")
            create_first_admin(email, password, first_name, last_name)
        except ValueError as error:
            raise click.ClickException(str(error)) from None
        click.echo("Administrator created.")

    return app
