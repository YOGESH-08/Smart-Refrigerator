from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.schemas import RFIDItemUpdatePayload, RFIDScanPayload

rfid_bp = Blueprint("rfid_api", __name__, url_prefix="/api/v1/rfid")


@rfid_bp.post("/scans")
def create_rfid_scan():
    if request.headers.get("X-API-Key") != current_app.config["API_KEY"]:
        return jsonify({"error": "Unauthorized", "code": "invalid_api_key"}), 401
    try:
        payload = RFIDScanPayload.model_validate(request.get_json(silent=True) or {})
    except Exception as exc:
        return jsonify({"error": "Bad request", "code": "invalid_payload", "details": {"message": str(exc)}}), 400
    scan = current_app.extensions["repo"].insert_rfid_scan(payload.model_dump())
    return jsonify({"data": scan, "meta": {"status": "stored"}}), 201


@rfid_bp.get("/scans")
def list_rfid_scans():
    try:
        limit = max(1, min(int(request.args.get("limit", "20")), 100))
    except ValueError:
        return jsonify({"error": "Bad request", "code": "invalid_limit"}), 400
    scans = current_app.extensions["repo"].get_rfid_scans(limit)
    return jsonify({"data": scans, "meta": {"count": len(scans)}}), 200


@rfid_bp.get("/items")
def list_rfid_items():
    items = current_app.extensions["repo"].get_rfid_items()
    return jsonify({"data": items, "meta": {"count": len(items)}}), 200


@rfid_bp.put("/items/<uid>")
def update_rfid_item(uid: str):
    try:
        payload = RFIDItemUpdatePayload.model_validate(request.get_json(silent=True) or {})
    except Exception as exc:
        return jsonify({"error": "Bad request", "code": "invalid_payload", "details": {"message": str(exc)}}), 400
    item = current_app.extensions["repo"].update_rfid_item(
        uid, payload.item_name, payload.quantity
    )
    if item is None:
        return jsonify({"error": "RFID tag not found", "code": "not_found"}), 404
    return jsonify({"data": item, "meta": {"status": "updated"}}), 200
