from flask import Flask
import atexit
from backend.rest_api.routes.truck_api import truck_api
from backend.rest_api.routes.mission_api import mission_api 
from backend.rest_api.routes.facility_api import facility_api
from backend.rest_api.routes.system_api import system_api, set_tcp_server_instance
from backend.rest_api.managers import cleanup_managers

# Flask 웹 서버 인스턴스 생성
flask_server = Flask(__name__)

# CORS 설정 추가 (필요시 주석 해제)
# from flask_cors import CORS
# CORS(flask_server)

# 블루프린트 등록 - 모든 라우트에 '/api' 프리픽스 추가
flask_server.register_blueprint(truck_api, url_prefix='/api')
flask_server.register_blueprint(mission_api, url_prefix='/api')
flask_server.register_blueprint(facility_api, url_prefix='/api')
flask_server.register_blueprint(system_api, url_prefix='/api/system')

# 디버깅용 경로 출력 함수 추가
def print_registered_routes():
    """등록된 모든 URL 규칙 출력"""
    print("\n[등록된 URL 규칙]")
    for rule in flask_server.url_map.iter_rules():
        print(f"  {rule} - 메서드: {', '.join(rule.methods)}")
    print("")

# TCP 서버 인스턴스를 system_api 모듈에 전달하는 함수
def init_tcp_server_reference(tcp_server):
    print("[INFO] TCP 서버 인스턴스를 system_api 모듈에 전달합니다.")
    set_tcp_server_instance(tcp_server)
    print_registered_routes()  # 경로 출력

# 애플리케이션 종료 시 리소스 정리 함수 등록
atexit.register(cleanup_managers)

# ------------------ 서버 시작 ----------------------------

if __name__ == "__main__":
    flask_server.run(host="0.0.0.0", port=5001, debug=True) 