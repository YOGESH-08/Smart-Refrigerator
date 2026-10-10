from flask import Flask

from .alerts import alerts_bp
from .devices import devices_bp
from .export import export_bp
from .readings import readings_bp
from .settings import settings_bp
from .web import web_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(readings_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(web_bp)
