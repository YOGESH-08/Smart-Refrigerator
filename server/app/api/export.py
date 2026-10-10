from __future__ import annotations

from flask import Blueprint, current_app, Response

export_bp = Blueprint("export_api", __name__, url_prefix="/api/v1")


@export_bp.get("/export.csv")
def export_csv():
    repo = current_app.extensions["repo"]
    csv_data = repo.export_csv()
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=smart-fridge-readings.csv"})
