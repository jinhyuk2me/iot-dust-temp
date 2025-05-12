# backend/tcpio/tcp_server.py

import traceback
import socket
import threading
import json
from backend.tcpio.protocol import TCPProtocol
from backend.main_controller.main_controller import MainController


class TCPServer:
    def __init__(self, host="0.0.0.0", port=8000, app_controller=None):
        self.host = host
        self.port = port
        self.clients = {}         # addr → socket
        self.truck_sockets = {}   # truck_id → socket
        self.running = False

        # MainController 초기화 및 트럭 소켓 맵 설정
        self.app = app_controller if app_controller else MainController(port_map={})
        self.app.set_truck_commander(self.truck_sockets)

    @staticmethod
    def is_port_in_use(port, host='0.0.0.0'):
        """주어진 포트가 이미 사용 중인지 확인합니다.
        
        Args:
            port (int): 확인할 포트 번호
            host (str): 확인할 호스트 주소
            
        Returns:
            bool: 포트가 사용 중이면 True, 아니면 False
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return False  # 바인딩 성공 - 포트가 사용 가능
            except OSError:
                return True   # 바인딩 실패 - 포트가 이미 사용 중
    
    @staticmethod
    def find_available_port(start_port=8001, max_port=8100, host='0.0.0.0'):
        """지정된 범위 내에서 사용 가능한 첫 번째 포트를 찾습니다.
        
        Args:
            start_port (int): 검색 시작 포트
            max_port (int): 검색 종료 포트
            host (str): 확인할 호스트 주소
            
        Returns:
            int: 사용 가능한 포트 번호, 없으면 None
        """
        for port in range(start_port, max_port + 1):
            if not TCPServer.is_port_in_use(port, host):
                return port
        return None

    def start(self):
        self.running = True
        
        try:
            # 새 소켓 생성
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # SO_REUSEADDR 및 SO_REUSEPORT 옵션 설정 (가능한 경우)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                # SO_REUSEPORT는 일부 플랫폼에서만 지원
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                # 지원하지 않는 플랫폼에서는 무시
                pass
            
            # 소켓 타임아웃 설정
            self.server_sock.settimeout(1.0)  # 1초 타임아웃으로 accept 대기
            
            # 바인딩 시도
            try:
                self.server_sock.bind((self.host, self.port))
            except OSError as e:
                if "Address already in use" in str(e):
                    print(f"[⚠️ 포트 {self.port} 사용 중] 5초 후 다시 시도...")
                    # 기존 소켓 닫기
                    self.server_sock.close()
                    # 5초 대기
                    import time
                    time.sleep(5)
                    # 새 소켓 생성 및 재시도
                    self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    except (AttributeError, OSError):
                        pass
                    self.server_sock.settimeout(1.0)
                    self.server_sock.bind((self.host, self.port))
                else:
                    raise
                
            self.server_sock.listen(5)  # 백로그 크기 명시적 설정
            print(f"[🚀 TCP 서버 시작] {self.host}:{self.port}")

            # 클라이언트 연결을 위한 루프
            while self.running:
                try:
                    client_sock, addr = self.server_sock.accept()
                    # 클라이언트 연결 타임아웃 설정
                    client_sock.settimeout(30.0)  # 클라이언트 소켓에 30초 타임아웃 설정
                    self.clients[addr] = client_sock
                    print(f"[✅ 클라이언트 연결됨] {addr}")

                    threading.Thread(
                        target=self.handle_client,
                        args=(client_sock, addr),
                        daemon=True
                    ).start()
                except socket.timeout:
                    # accept 타임아웃은 정상 - running 플래그 확인하고 계속
                    continue
                except OSError as e:
                    # 소켓이 닫혔거나 다른 소켓 오류 발생
                    if self.running:  # 정상 종료가 아닌 경우에만 오류 로깅
                        print(f"[⚠️ TCP 서버 소켓 오류] {e}")
                    break

        except Exception as e:
            print(f"[⚠️ TCP 서버 오류] {e}")
            print(traceback.format_exc())
        finally:
            self.stop()

    def handle_client(self, client_sock, addr):
        """클라이언트 연결 처리 메서드"""
        try:
            temp_truck_id = f"TEMP_{addr[1]}"
            self.truck_sockets[temp_truck_id] = client_sock
            self.app.set_truck_commander(self.truck_sockets)

            buffer = ""
            while True:
                try:
                    data = client_sock.recv(4096).decode()
                    if not data:
                        print(f"[❌ 연결 종료] {addr}")
                        break

                    buffer += data
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue

                        print(f"[📩 수신 원문] {line}")
                        
                        # ✅ 비 JSON 메시지 무시
                        if not line.startswith("{"):
                            print("[ℹ️ 비JSON 메시지 무시]")
                            continue

                        message = TCPProtocol.parse_message(line)
                        if not message:
                            print("[⚠️ 메시지 파싱 실패]")
                            continue

                        # ✅ 여기에서 무조건 truck_id 등록
                        truck_id = message.get("sender")
                        if truck_id:
                            if truck_id not in self.truck_sockets:
                                print(f"[🔗 등록] 트럭 '{truck_id}' 소켓 등록")
                                # ✅ 임시 트럭 ID 제거
                                if temp_truck_id in self.truck_sockets:
                                    del self.truck_sockets[temp_truck_id]
                            self.truck_sockets[truck_id] = client_sock
                            # ✅ AppController의 TruckCommandSender 업데이트
                            self.app.set_truck_commander(self.truck_sockets)

                        # ✅ 메시지 처리 위임
                        self.app.handle_message(message)

                except ConnectionResetError:
                    print(f"[⚠️ 연결 재설정] {addr}")
                    break
                except ConnectionAbortedError:
                    print(f"[⚠️ 연결 중단] {addr}")
                    break
                except socket.timeout:
                    print(f"[⚠️ 소켓 타임아웃] {addr}")
                    break
                except Exception as e:
                    print(f"[⚠️ 에러] {addr} → {e}")
                    break

        finally:
            # 여기서 클라이언트 소켓을 닫고 정리합니다
            try:
                # 클라이언트 소켓 닫기
                client_sock.close()
                
                # 트럭 매핑에서 제거
                for truck_id, sock in list(self.truck_sockets.items()):
                    if sock == client_sock:
                        del self.truck_sockets[truck_id]
                        print(f"[🔌 트럭 연결 종료] {truck_id}")
                
                # 클라이언트 딕셔너리에서 제거
                if addr in self.clients:
                    del self.clients[addr]
                    
                # AppController의 TruckCommandSender 업데이트
                self.app.set_truck_commander(self.truck_sockets)
            except Exception as e:
                print(f"[⚠️ 소켓 정리 오류] {addr} → {e}")

    def safe_stop(self):
        """서버 소켓 및 모든 클라이언트 연결만 종료 (리소스 유지)"""
        # 먼저 running 플래그를 False로 설정
        old_running = self.running
        self.running = False
        
        if not old_running:
            # 이미 중지된 경우 중복 실행 방지
            return
        
        print("[🛑 TCP 서버 안전 종료 시작]")
        
        # 모든 클라이언트 소켓 정리
        for addr, sock in list(self.clients.items()):
            try:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
                print(f"[🔌 클라이언트 연결 종료] {addr}")
            except Exception as e:
                print(f"[⚠️ 클라이언트 소켓 닫기 오류] {addr} → {e}")
        
        # 서버 소켓 닫기
        try:
            if hasattr(self, 'server_sock'):
                try:
                    self.server_sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass  # shutdown이 실패해도 close는 진행
                self.server_sock.close()
                print("[🔌 서버 소켓 종료됨]")
        except Exception as e:
            print(f"[⚠️ 서버 소켓 닫기 오류] {e}")
        
        # 연결 정보 초기화 (참조는 유지)
        self.clients.clear()
        self.truck_sockets.clear()
        
        print("[🔌 TCP 서버 안전 종료됨 (리소스는 유지됨)]")

    def stop(self):
        """서버 소켓 및 모든 클라이언트 연결 종료 + 리소스 정리
        
        주의: 이 메서드는 전체 리소스를 정리하므로 재시작 시에는 safe_stop을 사용해야 함
        """
        # 이미 종료된 경우 처리
        if not self.running and not hasattr(self, 'server_sock'):
            return
            
        # 먼저 안전하게 소켓 종료
        self.safe_stop()
        
        # 여기서부터는 전체 리소스 정리 과정
        # MainController 등의 리소스는 건드리지 않음
        print("[🛑 TCP 서버 완전 종료됨]")

    def send_command(self, client_socket, cmd, payload=None):
        msg = {
            "sender": "SERVER",
            "receiver": "TRUCK_01",
            "cmd": cmd,
            "payload": payload or {}
        }
        try:
            client_socket.send((json.dumps(msg) + "\n").encode('utf-8'))
            print(f"[📤 {cmd} 전송] {client_socket.getpeername()}")
        except Exception as e:
            print(f"[❌ 전송 오류] {e}") 