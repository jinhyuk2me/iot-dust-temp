from flask import Blueprint, jsonify, request
from backend.tcpio.tcp_server import TCPServer
import threading
import time
import traceback

# 블루프린트 생성
system_api = Blueprint('system_api', __name__)

# TCP 서버 인스턴스 참조
_tcp_server_instance = None

def set_tcp_server_instance(tcp_server_instance):
    """TCP 서버 인스턴스 설정"""
    global _tcp_server_instance
    _tcp_server_instance = tcp_server_instance

@system_api.route('/tcp/restart', methods=['POST'])
def restart_tcp_server():
    """TCP 서버 재시작
    
    기존 TCP 서버를 중지하고 새로운 TCP 서버를 시작합니다.
    """
    global _tcp_server_instance
    
    print("[DEBUG] TCP 서버 재시작 API 엔드포인트 호출됨")
    
    if not _tcp_server_instance:
        print("[ERROR] TCP 서버 인스턴스가 설정되지 않았습니다.")
        return jsonify({"success": False, "message": "TCP 서버 인스턴스가 설정되지 않았습니다."}), 404
    
    # TCP 서버의 중요 정보 백업
    host = _tcp_server_instance.host
    port = _tcp_server_instance.port
    app_controller = _tcp_server_instance.app  # MainController 인스턴스 참조 유지
    
    # 원래 TCP 서버 인스턴스 백업 (복원에 사용)
    original_instance = _tcp_server_instance
    
    def restart_server_thread():
        global _tcp_server_instance
        try:
            # 1. 기존 서버 종료 (안전하게 소켓만 닫음)
            print("[INFO] TCP 서버 재시작 요청 처리 중...")
            
            # 안전하게 서버 종료 (리소스 보존, stop() 메서드 호출하지 않음)
            if hasattr(_tcp_server_instance, 'safe_stop'):
                _tcp_server_instance.safe_stop()
            else:
                # safe_stop이 없는 경우 직접 소켓만 닫기
                try:
                    if hasattr(_tcp_server_instance, 'server_sock') and _tcp_server_instance.server_sock:
                        _tcp_server_instance.server_sock.close()
                    _tcp_server_instance.running = False
                except Exception as e:
                    print(f"[WARN] TCP 서버 소켓 닫기 실패: {e}")
            
            # 잠시 대기 (소켓 정리 시간)
            time.sleep(2)  # 대기 시간 증가 (1초 → 2초)
            
            # 2. 새 TCP 서버 인스턴스 생성 및 시작
            from backend.tcpio.tcp_server import TCPServer
            
            # 원래 포트를 사용할 수 있는지 확인
            if not TCPServer.is_port_in_use(port, host):
                # 같은 포트로 새 인스턴스 생성 시도
                print(f"[INFO] 동일한 포트({port})로 TCP 서버 재생성...")
                new_instance = TCPServer(host, port, app_controller)
                new_port = port
            else:
                # 사용 가능한 포트 검색
                new_port = TCPServer.find_available_port(port + 1, port + 100, host)
                if new_port:
                    print(f"[INFO] 대체 포트({new_port})로 TCP 서버 재생성...")
                    new_instance = TCPServer(host, new_port, app_controller)
                else:
                    raise Exception(f"사용 가능한 포트를 찾을 수 없습니다. (범위: {port+1}~{port+100})")
            
            try:
                # API 모듈에 새 인스턴스 설정 (기존 인스턴스를 교체)
                _tcp_server_instance = new_instance
                set_tcp_server_instance(_tcp_server_instance)
                
                # 새 인스턴스 시작 (데몬 스레드로 실행)
                server_thread = threading.Thread(target=_tcp_server_instance.start, daemon=True)
                server_thread.start()
                
                # 시작 확인을 위한 짧은 대기
                time.sleep(0.5)
                
                print(f"[INFO] TCP 서버 재시작 성공 (포트: {new_port})")
                
            except Exception as e:
                print(f"[ERROR] TCP 서버 시작 실패: {e}")
                # 원래 인스턴스로 복원
                _tcp_server_instance = original_instance
                set_tcp_server_instance(_tcp_server_instance)
                print("[INFO] 원래 TCP 서버 인스턴스로 복원됨")
                raise
                    
        except Exception as e:
            print(f"[ERROR] TCP 서버 재시작 실패: {e}")
            print(f"[ERROR] 상세 오류: {traceback.format_exc()}")
            
            # 재시작 실패 시 원래 인스턴스로 복원
            try:
                if _tcp_server_instance != original_instance:
                    _tcp_server_instance = original_instance
                    set_tcp_server_instance(_tcp_server_instance)
                    print("[INFO] 재시작 실패로 원래 TCP 서버 인스턴스로 복원됨")
            except:
                # 복원 중 에러 발생할 경우 무시 (중복 복원 방지)
                pass
    
    # 별도 스레드에서 재시작 처리
    threading.Thread(target=restart_server_thread, daemon=True).start()
    
    print("[DEBUG] TCP 서버 재시작 요청 성공적으로 처리됨")
    return jsonify({
        "success": True,
        "message": "TCP 서버 재시작 요청이 성공적으로 처리되었습니다."
    })

@system_api.route('/status', methods=['GET'])
def get_system_status():
    """시스템 상태 조회
    
    현재 시스템 상태 정보를 반환합니다.
    """
    # TCP 서버 상태 확인
    tcp_server_running = _tcp_server_instance is not None and _tcp_server_instance.running
    
    # 시스템 상태 정보
    status = {
        "tcp_server": {
            "running": tcp_server_running,
            "clients_count": len(_tcp_server_instance.clients) if tcp_server_running else 0,
            "trucks_count": len(_tcp_server_instance.truck_sockets) if tcp_server_running else 0
        }
    }
    
    # TCP 서버 상세 정보 추가
    if _tcp_server_instance:
        status["tcp_server"].update({
            "host": _tcp_server_instance.host,
            "port": _tcp_server_instance.port,
            "connected_clients": [f"{addr[0]}:{addr[1]}" for addr in _tcp_server_instance.clients.keys()] if hasattr(_tcp_server_instance, 'clients') else [],
            "connected_trucks": list(_tcp_server_instance.truck_sockets.keys()) if hasattr(_tcp_server_instance, 'truck_sockets') else []
        })
    
    return jsonify(status)

@system_api.route('/tcp/status', methods=['GET'])
def get_tcp_server_status():
    """TCP 서버 상태 조회
    
    현재 TCP 서버의 상세 상태 정보를 반환합니다.
    """
    global _tcp_server_instance
    
    if not _tcp_server_instance:
        return jsonify({
            "success": False,
            "message": "TCP 서버 인스턴스가 설정되지 않았습니다."
        }), 404
    
    # TCP 서버 상태 정보
    return jsonify({
        "success": True,
        "status": {
            "running": _tcp_server_instance.running,
            "host": _tcp_server_instance.host,
            "port": _tcp_server_instance.port,
            "clients_count": len(_tcp_server_instance.clients) if hasattr(_tcp_server_instance, 'clients') else 0,
            "trucks_count": len(_tcp_server_instance.truck_sockets) if hasattr(_tcp_server_instance, 'truck_sockets') else 0,
            "connected_clients": [f"{addr[0]}:{addr[1]}" for addr in _tcp_server_instance.clients.keys()] if hasattr(_tcp_server_instance, 'clients') else [],
            "connected_trucks": list(_tcp_server_instance.truck_sockets.keys()) if hasattr(_tcp_server_instance, 'truck_sockets') else []
        }
    }) 