from flask import Blueprint, jsonify, request
from backend.rest_api.managers import get_mission_manager

# 미션 관련 API 블루프린트 생성
mission_api = Blueprint('mission_api', __name__)

# ------------------ 미션 API ----------------------------

@mission_api.route("/missions", methods=["GET"])
def get_all_missions():
    """전체 미션 조회"""
    manager = get_mission_manager()
    missions = manager.get_assigned_and_waiting_missions()
    return jsonify([mission.to_dict() for mission in missions])


@mission_api.route("/missions/<mission_id>", methods=["GET"])
def get_mission(mission_id):
    """특정 미션 조회"""
    manager = get_mission_manager()
    mission = manager.find_mission_by_id(mission_id)
    if mission:
        return jsonify(mission.to_dict())
    return jsonify({"error": "Mission not found"}), 404


@mission_api.route("/missions", methods=["POST"])
def create_mission():
    """새 미션 생성"""
    data = request.json
    manager = get_mission_manager()
    try:
        mission = manager.create_mission(
            mission_id=data["mission_id"],
            cargo_type=data["cargo_type"],
            cargo_amount=float(data["cargo_amount"]),
            source=data["source"],
            destination=data["destination"]
        )
        if mission:
            return jsonify(mission.to_dict()), 201
        return jsonify({"error": "Mission creation failed"}), 500
    except Exception as err:
        print(f"[ERROR] 미션 생성 실패: {err}")
        return jsonify({"error": str(err)}), 500


@mission_api.route("/missions/<mission_id>/complete", methods=["POST"])
def complete_mission(mission_id):
    """미션 완료 처리"""
    manager = get_mission_manager()
    if manager.complete_mission(mission_id):
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Mission completion failed"}), 500


@mission_api.route("/missions/<mission_id>/cancel", methods=["POST"])
def cancel_mission(mission_id):
    """미션 취소 처리"""
    manager = get_mission_manager()
    if manager.cancel_mission(mission_id):
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Mission cancellation failed"}), 500 