from flask import Flask

from routers.admin import admin_bp
from routers.auth import auth_bp
from routers.dashboard import dashboard_bp
from routers.jobs import jobs_bp
from utils import get_current_user, init_db


def create_app():
    app = Flask(__name__)
    app.secret_key = "dev-placement-portal-secret"

    init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(jobs_bp)

    @app.context_processor
    def inject_current_user():
        return {"current_user": get_current_user()}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)