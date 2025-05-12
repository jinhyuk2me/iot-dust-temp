import signal
import sys, os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from backend.main_controller.main_controller import MainController
from backend.tcpio.tcp_server import TCPServer
from backend.mission.mission import Mission
from backend.mission.mission_db import MissionDB
from backend.mission.mission_status import MissionStatus
from backend.truck_status.truck_status_db import TruckStatusDB
from backend.facility_status.facility_status_manager import FacilityStatusManager
from backend.facility_status.facility_status_db import FacilityStatusDB
import threading
from backend.rest_api.app import flask_server, init_tcp_server_reference  # app.py에서 Flask 서버와 초기화 함수 가져오기

# 설정
HOST = '0.0.0.0'
PORT = 8001

# 포트 맵: 시리얼 장치 연결에 사용됨
port_map = {
    # 실제 장치 연결 설정
    "GATE_A": "/dev/ttyACM1",  # 게이트 A, B가 같은 아두이노에 연결됨
    "GATE_B": "/dev/ttyACM1",  # 게이트 A, B에 동일한 포트 지정
    "BELT": "/dev/ttyACM0"     # 벨트는 실제 장치로 연결
}

print("[초기화] 포트 맵:", port_map)

# 하드웨어 사용 여부 설정
USE_FAKE_HARDWARE = True  # 전체 가상 모드 여부 (True로 설정)

# 특정 장치만 가상 모드로 설정 (모든 장치 실제 연결)
FAKE_DEVICES = []  # 가상 모드로 실행할 장치 목록(비워둠)

# 디버그 모드 설정
DEBUG_MODE = False  # 디버그 로그를 출력하지 않음 (필요시 True로 변경)

print(f"[초기화] 하드웨어 설정: 기본 모드={'가상' if USE_FAKE_HARDWARE else '실제'}, 가상 장치={FAKE_DEVICES}")
print(f"[초기화] 디버그 모드: {'활성화' if DEBUG_MODE else '비활성화'}")

# DB 연결 설정
mission_db = MissionDB(
    host="localhost",
    user="root",
    password="jinhyuk2dacibul",
    database="dust"
)

# 트럭 상태 데이터베이스 설정 및 초기화
truck_status_db = TruckStatusDB(
    host="localhost",
    user="root",
    password="jinhyuk2dacibul",
    database="dust"
)

# 시설 상태 데이터베이스 설정 및 초기화
facility_status_db = FacilityStatusDB(
    host="localhost",
    user="root",
    password="jinhyuk2dacibul",
    database="dust"
)

# 트럭 상태 초기화 - 시뮬레이터 시작 시마다 상태 리셋
truck_status_db.reset_all_statuses()

# 시설 상태 매니저 생성
facility_status_manager = FacilityStatusManager(facility_status_db)

# MainController 인스턴스 생성 (시설 상태 매니저 전달)
main_controller = MainController(
    port_map=port_map, 
    use_fake=USE_FAKE_HARDWARE, 
    fake_devices=FAKE_DEVICES,
    debug=DEBUG_MODE,
    facility_status_manager=facility_status_manager
)

# 앱의 트럭 상태 초기화 (메모리에 있는 상태도 초기화)
main_controller.truck_status_manager.reset_all_trucks()

# 시설 상태 초기화
facility_status_manager.reset_all_facilities()

# 기존 미션 확인
print("[🔍 기존 미션 확인 중...]")
waiting_missions = mission_db.get_waiting_missions()
print(f"[ℹ️ 기존 미션 발견] 총 {len(waiting_missions)}개의 대기 중인 미션이 있습니다.")

# TCP 서버 실행
server = TCPServer(HOST, PORT, main_controller)

# TCP 서버 인스턴스를 시스템 API에 전달
init_tcp_server_reference(server)

# Flask 서버 실행 함수
def run_flask():
    flask_server.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)

# 종료 신호 핸들링
def signal_handler(sig, frame):
    print("[🛑 서버 종료 요청됨]")
    
    # 실행 중인 모든 미션을 취소 상태로 변경
    print("[⚠️ 실행 중인 미션 취소 중...]")
    waiting_missions = mission_db.get_waiting_missions()
    for mission_data in waiting_missions:
        mission = Mission.from_row(mission_data)
        main_controller.mission_manager.cancel_mission(mission.mission_id)
    print(f"[✅ {len(waiting_missions)}개의 미션이 취소되었습니다.]")
    
    server.stop()
    mission_db.close()  # DB 연결 종료
    truck_status_db.close()  # 트럭 상태 DB 연결 종료
    facility_status_db.close()  # 시설 상태 DB 연결 종료
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print(f"[메인 서버 시작됨] TCP 서버: {HOST}:{PORT}, Flask 서버: 0.0.0.0:5001")


if __name__ == "__main__":
    # TCP 서버를 별도 데몬 스레드로 시작 (중요: 데몬 스레드로 실행하여 메인 스레드와 독립적으로 동작)
    tcp_thread = threading.Thread(target=server.start, daemon=True)
    tcp_thread.start()
    
    # Flask 서버를 메인 스레드에서 시작 (중요: 메인 프로세스로 실행하여 TCP 서버가 종료되어도 Flask 서버는 유지)
    run_flask() 