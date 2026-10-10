from __future__ import annotations

from flask import Blueprint, render_template

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def overview():
    return render_template("overview.html")


@web_bp.get("/analytics")
def analytics():
    return render_template("analytics.html")


@web_bp.get("/alerts")
def alerts():
    return render_template("alerts.html")


@web_bp.get("/device")
def device_page():
    return render_template("device.html")
