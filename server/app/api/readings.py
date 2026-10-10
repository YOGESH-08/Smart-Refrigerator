from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from app.schemas import ReadingPayload
from app.services.alert_engine import build_alert_records

readings_bp = Blueprint("readings_api", __name__, url_prefix="/api/v1")


def _require_api_key() -> None:
    api_key = request.headers.get("X-API-Key")
    if api_key != current_app.config["API_KEY"]:
        raise ValueError("Invalid or missing API key")


@readings_bp.post("/readings")
def create_reading():
    try:
        _require_api_key()
        payload = ReadingPayload.model_validate(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"error": "Bad request", "code": "invalid_payload", "details": {"message": str(exc)}}), 400
    except Exception as exc:  # pragma: no cover - guardrail
        return jsonify({"error": "Bad request", "code": "invalid_payload", "details": {"message": str(exc)}}), 400

    repo = current_app.extensions["repo"]
    reading = payload.model_dump()
    result = repo.insert_reading(reading)
    thresholds = repo.get_settings()
    baseline = float(thresholds.get("baseline_gas", 120.0))
    alert_records = build_alert_records(reading, thresholds, baseline)
    for alert in alert_records:
        repo.upsert_alert(alert)
    return jsonify({"data": result, "meta": {"status": "stored", "alerts": len(alert_records)}}), 201


@readings_bp.get("/readings/latest")
def latest_reading():
    repo = current_app.extensions["repo"]
    device_id = request.args.get("device_id")
    reading = repo.get_latest_reading(device_id)
    if reading is None:
        return jsonify({"data": None, "meta": {"count": 0}}), 200
    return jsonify({"data": reading, "meta": {"count": 1}}), 200


@readings_bp.get("/readings")
def list_readings():
    from_ts = request.args.get("from")
    to_ts = request.args.get("to")
    bucket = request.args.get("bucket", "raw")
    repo = current_app.extensions["repo"]
    readings = repo.get_readings(from_ts, to_ts, bucket)
    return jsonify({"data": readings, "meta": {"count": len(readings), "bucket": bucket}}), 200
