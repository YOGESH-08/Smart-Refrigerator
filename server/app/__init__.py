from __future__ import annotations

from flask import Flask

from app.api import register_blueprints
from app.config import Config
from app.repository.repository import Repository


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    repo = Repository(app.config["DATABASE_PATH"])
    repo.init_db()
    app.extensions["repo"] = repo

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "smart-fridge-api", "database": app.config["DATABASE_PATH"]}

    @app.errorhandler(400)
    def bad_request(error):
        return {"error": "Bad request", "code": "bad_request", "details": {"message": str(error)}}, 400

    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found", "code": "not_found", "details": {"message": str(error)}}, 404

    @app.errorhandler(500)
    def server_error(error):
        return {"error": "Internal server error", "code": "internal_error", "details": {"message": str(error)}}, 500

    register_blueprints(app)
    return app
