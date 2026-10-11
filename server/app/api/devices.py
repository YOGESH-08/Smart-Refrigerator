from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

devices_bp = Blueprint("devices_api", __name__, url_prefix="/api/v1")


@devices_bp.get("/device/status")
def device_status():
    repo = current_app.extensions["repo"]
    device_id = request.args.get("device_id")
    status = repo.get_device_status(device_id)
    return jsonify({"data": status, "meta": {"device_id": device_id}}), 200
