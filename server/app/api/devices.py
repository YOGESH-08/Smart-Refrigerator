from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

devices_bp = Blueprint("devices_api", __name__, url_prefix="/api/v1")


@devices_bp.get("/device/status")
def device_status():
    repo = current_app.extensions["repo"]
    device_id = request.args.get("device_id")
    status = repo.get_device_status(device_id)
    return jsonify({"data": status, "meta": {"device_id": device_id}}), 200


@devices_bp.get("/device/commands")
def device_commands():
    if request.headers.get("X-API-Key") != current_app.config["API_KEY"]:
        return jsonify({"error": "Unauthorized"}), 401
    device_id = request.args.get("device_id", "").strip()
    if not device_id:
        return jsonify({"error": "device_id is required"}), 400
    commands = current_app.extensions["repo"].consume_device_commands(device_id)
    return jsonify({"data": commands}), 200
