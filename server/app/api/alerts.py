from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.schemas import AlertAckPayload

alerts_bp = Blueprint("alerts_api", __name__, url_prefix="/api/v1")


@alerts_bp.get("/alerts")
def list_alerts():
    repo = current_app.extensions["repo"]
    status = request.args.get("status")
    severity = request.args.get("severity")
    alerts = repo.get_alerts(status, severity)
    return jsonify({"data": alerts, "meta": {"count": len(alerts)}}), 200


@alerts_bp.post("/alerts")
def create_alert():
    payload = request.get_json(silent=True) or {}
    try:
        alert_id = int(payload.get("id", 0) or 0)
        device_id = str(payload.get("device_id") or "device-01").strip()
        alert_type = str(payload.get("alert_type") or "temperature_high").strip()
        severity = str(payload.get("severity") or "medium").strip()
        message = str(payload.get("message") or "Alert generated").strip()
    except (TypeError, ValueError):
        return jsonify({"error": "Bad request", "code": "invalid_payload", "details": {"message": "Alert payload invalid"}}), 400

    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds")
    repo = current_app.extensions["repo"]
    alert = {
        "device_id": device_id,
        "alert_type": alert_type,
        "severity": severity,
        "status": "active",
        "message": message,
        "first_seen": now,
        "last_triggered": now,
        "acked": None,
        "resolved_at": None,
    }
    stored = repo.upsert_alert(alert)
    return jsonify({"data": stored, "meta": {"status": "created"}}), 201


@alerts_bp.post("/alerts/<int:alert_id>/ack")
def acknowledge_alert(alert_id: int):
    repo = current_app.extensions["repo"]
    payload = request.get_json(silent=True) or {}
    try:
        ack = AlertAckPayload.model_validate(payload)
    except Exception as exc:  # pragma: no cover - validation guard
        return jsonify({"error": "Bad request", "code": "invalid_payload", "details": {"message": str(exc)}}), 400
    try:
        updated = repo.acknowledge_alert(alert_id, ack.acknowledged_by)
    except ValueError:
        return jsonify({"error": "Not found", "code": "alert_missing", "details": {"message": "Alert does not exist"}}), 404
    return jsonify({"data": updated, "meta": {"status": "acknowledged"}}), 200
