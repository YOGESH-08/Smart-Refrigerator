from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.schemas import ThresholdsPayload

settings_bp = Blueprint("settings_api", __name__, url_prefix="/api/v1")


@settings_bp.get("/settings/thresholds")
def get_thresholds():
    repo = current_app.extensions["repo"]
    return jsonify({"data": repo.get_settings(), "meta": {"count": len(repo.get_settings())}}), 200


@settings_bp.put("/settings/thresholds")
def update_thresholds():
    payload = request.get_json(silent=True) or {}
    try:
        validated = ThresholdsPayload.model_validate(payload)
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": "Bad request", "code": "invalid_payload", "details": {"message": str(exc)}}), 400
    repo = current_app.extensions["repo"]
    updated = repo.save_thresholds(validated.model_dump())
    return jsonify({"data": updated, "meta": {"status": "updated"}}), 200


@settings_bp.post("/settings/baseline/reset")
def reset_baseline():
    repo = current_app.extensions["repo"]
    current = repo.get_settings().get("baseline_gas", 120.0)
    baseline = repo.save_baseline(float(current))
    return jsonify({"data": {"baseline_gas": baseline}, "meta": {"status": "reset"}}), 200
