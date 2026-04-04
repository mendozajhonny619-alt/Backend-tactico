from flask import Blueprint, jsonify
from app.services.dashboard_service import DashboardService
from app.services.history_service import HistoryService

api_bp = Blueprint("api", __name__)

@api_bp.route("/", methods=["GET"])
def home():
    return jsonify({
        "ok": True,
        "service": "JHONNY_ELITE V16",
        "message": "API operativa"
    }), 200

@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify(DashboardService.healthcheck()), 200

@api_bp.route("/stats", methods=["GET"])
def stats():
    return jsonify(DashboardService.get_stats()), 200

@api_bp.route("/history", methods=["GET"])
def history():
    return jsonify(DashboardService.get_history_panel()), 200
