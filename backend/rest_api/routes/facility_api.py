from flask import Blueprint, jsonify, request
from backend.rest_api.managers import get_facility_status_manager
from backend.serialio.device_manager import DeviceManager
from backend.main_controller.main_controller import MainController

# 시설 관련 API 블루프린트 생성
facility_api = Blueprint('facility_api', __name__)

# 장치 관리자와 컨트롤러 참조
device_manager = None
gate_controllers = {}
belt_controller = None

def get_controllers():
    """필요한 컨트롤러들을 초기화합니다."""
    global device_manager, gate_controllers, belt_controller
    
    # 이미 초기화됐으면 반환
    if device_manager is not None:
        return
    
    # 현재 운영 환경에 맞는 포트맵 설정
    # 실제 배포 환경에서는 설정 파일이나 환경 변수에서 읽어오도록 수정
    port_map = {
        "GATE_A": "/dev/ttyUSB0",
        "GATE_B": "/dev/ttyUSB1",
        "BELT": "/dev/ttyUSB2"
    }
    
    # 상태 관리자 참조
    facility_status_manager = get_facility_status_manager()
    
    # 장치 관리자 초기화 (가능하면 MainController에서 가져옴)
    try:
        # 테스트 환경에서는 가짜 장치 사용
        use_fake = True  # 실제 환경에서는 False로 설정
        device_manager = DeviceManager(
            port_map=port_map,
            use_fake=use_fake,
            facility_status_manager=facility_status_manager
        )
        
        # 게이트 컨트롤러 참조
        gate_controllers = {
            gate_id: device_manager.get_controller(gate_id)
            for gate_id in ["GATE_A", "GATE_B"]
            if device_manager.get_controller(gate_id) is not None
        }
        
        # 벨트 컨트롤러 참조
        belt_controller = device_manager.get_controller("BELT")
        
        if not gate_controllers:
            print("[⚠️ 경고] 사용 가능한 게이트 컨트롤러가 없습니다")
            
        if not belt_controller:
            print("[⚠️ 경고] 벨트 컨트롤러를 찾을 수 없습니다")
            
    except Exception as e:
        print(f"[ERROR] 장치 컨트롤러 초기화 실패: {e}")

# ------------------ 시설 상태 API ----------------------------

# 전체 시설 상태 조회
@facility_api.route("/facilities", methods=["GET"])
def get_all_facilities():
    manager = get_facility_status_manager()
    facilities = manager.get_all_facilities()
    return jsonify(facilities)

# 특정 게이트 상태 조회
@facility_api.route("/facilities/gates/<gate_id>", methods=["GET"])
def get_gate_status(gate_id):
    manager = get_facility_status_manager()
    gate_status = manager.get_gate_status(gate_id)
    return jsonify(gate_status)

# 특정 벨트 상태 조회
@facility_api.route("/facilities/belt/<belt_id>", methods=["GET"])
def get_belt_status(belt_id):
    manager = get_facility_status_manager()
    belt_status = manager.get_belt_status(belt_id)
    return jsonify(belt_status)

# 모든 게이트 상태 조회
@facility_api.route("/facilities/gates", methods=["GET"])
def get_all_gates():
    manager = get_facility_status_manager()
    facilities = manager.get_all_facilities()
    
    # 게이트만 필터링
    gates = {k: v for k, v in facilities.items() if k.startswith("GATE_")}
    return jsonify(gates)

# 모든 벨트 상태 조회
@facility_api.route("/facilities/belts", methods=["GET"])
def get_all_belts():
    manager = get_facility_status_manager()
    facilities = manager.get_all_facilities()
    
    # 벨트만 필터링
    belts = {k: v for k, v in facilities.items() if k.startswith("BELT")}
    return jsonify(belts)

# 게이트 히스토리 조회
@facility_api.route("/facilities/gates/<gate_id>/history", methods=["GET"])
def get_gate_history(gate_id):
    manager = get_facility_status_manager()
    limit = request.args.get('limit', default=100, type=int)
    history = manager.get_gate_history(gate_id, limit)
    return jsonify(history)

# 벨트 히스토리 조회
@facility_api.route("/facilities/belt/<belt_id>/history", methods=["GET"])
def get_belt_history(belt_id):
    manager = get_facility_status_manager()
    limit = request.args.get('limit', default=100, type=int)
    history = manager.get_belt_history(belt_id, limit)
    return jsonify(history)

# ------------------ 시설 제어 API ----------------------------

# 게이트 제어
@facility_api.route("/facilities/gates/<gate_id>/control", methods=["POST"])
def control_gate(gate_id):
    """게이트 제어 API
    
    요청 본문 예시:
    {
        "command": "open" 또는 "close"
    }
    """
    data = request.json
    
    if not data or "command" not in data:
        return jsonify({"error": "command 필드가 필요합니다."}), 400
        
    command = data["command"].lower()
    if command not in ["open", "close"]:
        return jsonify({"error": "command는 'open' 또는 'close'만 가능합니다."}), 400
    
    # 컨트롤러 초기화 확인
    get_controllers()
    
    # 게이트 컨트롤러 획득
    gate_controller = gate_controllers.get(gate_id)
    if not gate_controller:
        return jsonify({"error": f"{gate_id} 컨트롤러를 찾을 수 없습니다."}), 500
    
    try:
        success = False
        if command == "open":
            success = gate_controller.open_gate(gate_id)
        else:
            success = gate_controller.close_gate(gate_id)
            
        # 결과에 따른 응답 반환
        if success:
            return jsonify({
                "status": "success",
                "message": f"게이트 {gate_id} {'열기' if command == 'open' else '닫기'} 명령 성공",
                "command": command
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"게이트 {gate_id} {'열기' if command == 'open' else '닫기'} 명령 실패",
                "command": command
            }), 500
    except Exception as e:
        print(f"[ERROR] 게이트 제어 실패: {e}")
        return jsonify({"error": str(e)}), 500

# 벨트 제어
@facility_api.route("/facilities/belt/<belt_id>/control", methods=["POST"])
def control_belt(belt_id):
    """벨트 제어 API
    
    요청 본문 예시:
    {
        "command": "start", "stop", "emergency_stop", "set_speed" 중 하나
        "speed": 0-100 사이의 정수 (command가 "start" 또는 "set_speed"일 때만 필요)
    }
    """
    data = request.json
    
    if not data or "command" not in data:
        return jsonify({"error": "command 필드가 필요합니다."}), 400
        
    command = data["command"].lower()
    if command not in ["start", "stop", "emergency_stop", "set_speed"]:
        return jsonify({"error": "command는 'start', 'stop', 'emergency_stop', 'set_speed' 중 하나여야 합니다."}), 400
    
    # 속도 설정이 필요한 명령인 경우 speed 확인
    if command in ["start", "set_speed"]:
        if "speed" not in data:
            return jsonify({"error": f"{command} 명령에는 speed 필드가 필요합니다."}), 400
            
        try:
            speed = int(data["speed"])
            if not (0 <= speed <= 100):
                return jsonify({"error": "speed는 0에서 100 사이의 값이어야 합니다."}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "speed는 정수여야 합니다."}), 400
    
    # 컨트롤러 초기화 확인
    get_controllers()
    
    # 벨트 컨트롤러 확인
    if not belt_controller:
        return jsonify({"error": "벨트 컨트롤러를 찾을 수 없습니다."}), 500
    
    try:
        success = False
        # BeltController에 맞는 명령으로 변환하여 전송
        if command == "start":
            speed = int(data["speed"])
            # BeltController의 명령 인터페이스에 맞게 실행
            # 직접 run 명령으로 변환 (BeltController.send_command 메서드에 맞게)
            success = belt_controller.send_command(belt_id, "RUN")
            # 속도 설정은 별도로 처리해야 할 수 있음
            message = f"벨트 {belt_id} 시작 (속도: {speed})"
        elif command == "stop":
            success = belt_controller.send_command(belt_id, "STOP")
            message = f"벨트 {belt_id} 정지"
        elif command == "emergency_stop":
            success = belt_controller.send_command(belt_id, "EMRSTOP")
            message = f"벨트 {belt_id} 비상 정지"
        elif command == "set_speed":
            # 속도 설정이 별도 명령으로 있다면 그 명령 사용
            # 없으면 실행 명령으로 처리
            speed = int(data["speed"])
            success = belt_controller.send_command(belt_id, "RUN")
            message = f"벨트 {belt_id} 속도 설정: {speed}"
            
        if success:
            return jsonify({
                "status": "success",
                "message": message
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"벨트 {belt_id} 제어 실패: {command}"
            }), 500
    except Exception as e:
        print(f"[ERROR] 벨트 제어 실패: {e}")
        return jsonify({"error": str(e)}), 500 