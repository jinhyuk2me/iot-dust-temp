from flask import Blueprint, jsonify, request
from backend.rest_api.managers import get_truck_status_manager

# 트럭 관련 API 블루프린트 생성
truck_api = Blueprint('truck_api', __name__)

# ------------------ 트럭 상태 API ----------------------------

# 전체 트럭 상태 조회
@truck_api.route("/trucks", methods=["GET"])
def get_all_trucks():
    manager = get_truck_status_manager()
    trucks = manager.get_all_trucks()
    
    # 기본값 설정 - 미등록 트럭 정보
    default_trucks = {
        "TRUCK_01": {
            "battery": {"level": 100.0, "is_charging": False},
            "position": {"location": "STANDBY", "status": "IDLE"},
            "fsm_state": "IDLE"
        },
        "TRUCK_02": {
            "battery": {"level": 0.0, "is_charging": False},
            "position": {"location": "UNKNOWN", "status": "IDLE"},
            "fsm_state": "IDLE"
        },
        "TRUCK_03": {
            "battery": {"level": 0.0, "is_charging": False},
            "position": {"location": "UNKNOWN", "status": "IDLE"},
            "fsm_state": "IDLE"
        }
    }
    
    # 트럭 데이터가 없는 경우 기본 상태 반환
    if not trucks:
        trucks = default_trucks
    else:
        # TRUCK_02, TRUCK_03이 없을 경우 추가
        if "TRUCK_02" not in trucks:
            trucks["TRUCK_02"] = default_trucks["TRUCK_02"]
        if "TRUCK_03" not in trucks:
            trucks["TRUCK_03"] = default_trucks["TRUCK_03"]
    
    # 응답 형식 통일 - position 객체에는 항상 location과 status 키가 있어야 함
    for truck_id, truck_data in trucks.items():
        position = truck_data.get("position", {})
        if "current" in position:
            position["location"] = position.pop("current")
        if "run_state" in position:
            position["status"] = position.pop("run_state")
    
    return jsonify(trucks)

# 특정 트럭 상태 조회
@truck_api.route("/trucks/<truck_id>", methods=["GET"])
def get_truck(truck_id):
    manager = get_truck_status_manager()
    truck = manager.get_truck_status(truck_id)
    if not truck:  # 트럭 데이터가 없는 경우 기본 상태 반환
        truck = {
            "battery": {"level": 100.0, "is_charging": False},
            "position": {"location": "STANDBY", "status": "IDLE"}
        }
    
    # 응답 형식 확인 - position 객체에는 항상 location과 status 키가 있어야 함
    position = truck.get("position", {})
    if "current" in position:
        position["location"] = position.pop("current")
    if "run_state" in position:
        position["status"] = position.pop("run_state")
    
    return jsonify(truck)

# 모든 트럭의 위치 조회
@truck_api.route("/trucks/positions", methods=["GET"])
def get_all_truck_positions():
    manager = get_truck_status_manager()
    trucks = manager.get_all_trucks()
    
    # 기본값 설정 - 미등록 트럭 정보
    default_trucks = {
        "TRUCK_01": {
            "position": {"location": "STANDBY", "status": "IDLE"}
        },
        "TRUCK_02": {
            "position": {"location": "UNKNOWN", "status": "IDLE"}
        },
        "TRUCK_03": {
            "position": {"location": "UNKNOWN", "status": "IDLE"}
        }
    }
    
    # 트럭 데이터가 없는 경우 기본 상태 반환
    if not trucks:
        trucks = default_trucks
    else:
        # TRUCK_02, TRUCK_03이 없을 경우 추가
        if "TRUCK_02" not in trucks:
            trucks["TRUCK_02"] = default_trucks["TRUCK_02"]
        if "TRUCK_03" not in trucks:
            trucks["TRUCK_03"] = default_trucks["TRUCK_03"]
    
    # 응답 형식 통일
    for truck_id, truck_data in trucks.items():
        position = truck_data.get("position", {})
        if "current" in position:
            position["location"] = position.pop("current")
        if "run_state" in position:
            position["status"] = position.pop("run_state")
    
    response_data = {
        truck_id: truck["position"]
        for truck_id, truck in trucks.items()
    }
    return jsonify(response_data)

# 특정 트럭의 위치 조회
@truck_api.route("/trucks/<truck_id>/position", methods=["GET"])
def get_truck_position(truck_id):
    manager = get_truck_status_manager()
    truck = manager.get_truck_status(truck_id)
    
    # 기본값 설정
    default_position = {"location": "UNKNOWN", "status": "IDLE"}
    
    # 트럭 데이터가 없거나 위치 정보가 없는 경우 기본 상태 반환
    if not truck or "position" not in truck:
        return jsonify(default_position)
    
    # 응답 형식 통일
    position = truck.get("position", {}).copy()
    if "current" in position:
        position["location"] = position.pop("current")
    if "run_state" in position:
        position["status"] = position.pop("run_state")
    
    return jsonify(position)

# 모든 트럭의 배터리 상태 조회
@truck_api.route("/trucks/batteries", methods=["GET"])
def get_all_truck_batteries():
    manager = get_truck_status_manager()
    trucks = manager.get_all_trucks()
    
    # 기본값 설정 - 미등록 트럭은 빈 데이터로 표시
    default_trucks = {
        "TRUCK_01": {"battery": {"level": 100.0, "is_charging": False}},
        "TRUCK_02": {"battery": {}},  # 빈 객체로 반환 (GUI에서 처리)
        "TRUCK_03": {"battery": {}}   # 빈 객체로 반환 (GUI에서 처리)
    }
    
    # 트럭 데이터가 없는 경우 기본 상태 반환
    if not trucks:
        trucks = default_trucks
    else:
        # TRUCK_02, TRUCK_03이 없을 경우 빈 배터리 객체 추가
        if "TRUCK_02" not in trucks:
            trucks["TRUCK_02"] = {"battery": {}}
        if "TRUCK_03" not in trucks:
            trucks["TRUCK_03"] = {"battery": {}}
    
    response_data = {
        truck_id: truck["battery"]
        for truck_id, truck in trucks.items()
    }
    return jsonify(response_data)

# 특정 트럭의 배터리 상태 조회
@truck_api.route("/trucks/<truck_id>/battery", methods=["GET"])
def get_truck_battery(truck_id):
    manager = get_truck_status_manager()
    truck = manager.get_truck_status(truck_id)
    
    # 기본값 설정
    default_battery = {"level": 0.0, "is_charging": False}
    
    # 트럭 데이터가 없거나 배터리 정보가 없는 경우 기본 상태 반환
    if not truck or "battery" not in truck:
        if truck_id == "TRUCK_01":  # TRUCK_01은 기본값이 다름
            default_battery["level"] = 100.0
        return jsonify(default_battery)
    
    return jsonify(truck["battery"])

# 특정 트럭 배터리 상태 업데이트
@truck_api.route("/trucks/<truck_id>/battery", methods=["POST"])
def update_truck_battery(truck_id):
    manager = get_truck_status_manager()
    data = request.json
    
    try:
        level = data.get("level", 0)
        is_charging = data.get("is_charging", False)
        
        # 배터리 상태 업데이트
        manager.update_battery(truck_id, level, is_charging)
        
        return jsonify({"status": "success", "message": f"{truck_id} 배터리 업데이트 완료"}), 200
    except Exception as e:
        print(f"[ERROR] 배터리 업데이트 실패: {e}")
        return jsonify({"error": str(e)}), 500

# 하위 호환성을 위한 이전 엔드포인트 (리디렉션)
@truck_api.route("/truck_position", methods=["GET"])
def legacy_get_truck_position():
    """하위 호환성을 위한 이전 엔드포인트"""
    return get_all_truck_positions()

@truck_api.route("/truck_battery", methods=["GET"])
def legacy_get_truck_battery():
    """하위 호환성을 위한 이전 엔드포인트"""
    return get_all_truck_batteries()

@truck_api.route("/truck_battery/<truck_id>", methods=["POST"])
def legacy_update_truck_battery(truck_id):
    """하위 호환성을 위한 이전 엔드포인트"""
    return update_truck_battery(truck_id) 