import socket
import json
import time
import sys, os
import requests  # API 요청을 위한 모듈

# 현재 스크립트 경로를 기준으로 프로젝트 루트 경로를 추가합니다
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from backend.serialio.device_manager import DeviceManager
import threading
import requests

# 서버 설정
HOST = '127.0.0.1'
PORT = 8001
API_PORT = 5001  # Flask API 서버 포트

# 포트 맵: 시리얼 장치 연결에 사용됨 - 서버와 동일한 설정 사용
port_map = {
    "GATE_A": "GATE_A",
    "GATE_B": "GATE_B",
    "BELT": "BELT"
}

# 실제 TCP 서버 포트 확인 함수
def get_actual_tcp_port():
    """API 서버에 요청하여 실제 TCP 서버 포트 번호를 확인합니다."""
    try:
        response = requests.get(f"http://{HOST}:{API_PORT}/api/system/tcp/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "status" in data:
                port = data["status"].get("port")
                if port:
                    print(f"[✅ TCP 포트 확인됨] 서버 포트: {port}")
                    return port
        print("[⚠️ TCP 포트 확인 실패] 기본 포트를 사용합니다.")
    except Exception as e:
        print(f"[⚠️ TCP 포트 확인 오류] {e}")
    return PORT  # 기본 포트 반환

# 시리얼 매니저 초기화 - 실제 포트 맵 사용
manager = DeviceManager(port_map=port_map, use_fake=True)

class TruckSimulator:
    def __init__(self):
        self.source = None
        self.client = None
        self.battery_level = 100
        self.charging = False
        self.current_position = "STANDBY"
        self.run_state = "IDLE"
        
        # 실제 TCP 서버 포트 확인
        global PORT
        PORT = get_actual_tcp_port()
        
        # 서버 연결
        if not self.connect():
            print("[⚠️ 초기화 경고] 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
            print("[ℹ️ 도움말] 'python run/run_main_server.py'를 실행하여 서버를 시작하세요.")
            print("[ℹ️ 도움말] 또는 이미 실행 중인 모든 서버 프로세스를 종료하고 다시 시작해보세요.")
        else:
            print("[✅ 초기화 완료] 서버에 성공적으로 연결되었습니다.")
        
        # 상태 업데이트 타이머 시작
        self.updating = True
        self.updater_thread = threading.Thread(target=self.status_update_timer, daemon=True)
        self.updater_thread.start()

    def __del__(self):
        """소멸자 - 자원 정리"""
        self.updating = False
        if self.client:
            try:
                self.client.close()
            except:
                pass

    # TCP 연결
    def connect(self):
        """서버에 연결 (최대 5회 재시도)"""
        # 기존 소켓 정리
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                print(f"[⚠️ 소켓 닫기 실패] {e}")
            self.client = None
        
        # 새 소켓 생성
        max_retries = 5
        retry_count = 0
        retry_delay = 2.0  # 초기 대기 시간
        
        while retry_count < max_retries:
            try:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.settimeout(5.0)  # 연결 시도에 5초 타임아웃 설정
                print(f"[TCP 연결] {HOST}:{PORT} (시도 {retry_count+1}/{max_retries})")
                self.client.connect((HOST, PORT))
                print(f"[TCP 연결 성공] {HOST}:{PORT}")
                # 연결 성공 후 타임아웃 늘림
                self.client.settimeout(30.0)
                # 헬로 메시지 즉시 전송
                self.send("HELLO", {"msg": "register"}, wait=False)
                return True
            except (ConnectionRefusedError, socket.timeout) as e:
                retry_count += 1
                print(f"[⚠️ 연결 실패] {e} - {'재시도 중...' if retry_count < max_retries else '재시도 횟수 초과'}")
                if retry_count < max_retries:
                    # 지수 백오프 - 재시도마다 대기 시간 증가
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 10.0)  # 최대 10초까지 증가
                else:
                    print("[❌ 연결 실패] 최대 재시도 횟수를 초과했습니다.")
                    return False
            except Exception as e:
                print(f"[❌ 연결 오류] 예상치 못한 오류가 발생했습니다: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 10.0)
                else:
                    return False
                    
        return False

    # 메시지 전송
    def send(self, cmd, payload={}, wait=True):
        """명령을 서버로 전송"""
        if not self.client:
            print("[⚠️ 연결 없음] 메시지 전송 전 연결 시도 중...")
            if not self.connect():
                print("[❌ 전송 실패] 서버에 연결할 수 없어 메시지를 전송할 수 없습니다.")
                return False
                
        msg = {
            "sender": "TRUCK_01",
            "receiver": "SERVER",
            "cmd": cmd,
            "payload": payload
        }
        data = json.dumps(msg) + "\n"
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.client.send(data.encode())
                print(f"[SEND] {cmd} → {payload}")
                if wait:
                    time.sleep(0.5)
                return True
            except (BrokenPipeError, ConnectionResetError, socket.timeout) as e:
                retry_count += 1
                print(f"[⚠️ 전송 오류] {e} - {'재시도 중...' if retry_count < max_retries else '재시도 횟수 초과'}")
                
                if retry_count < max_retries:
                    # 연결 재시도
                    print("[⚠️ 연결 끊김] 서버에 재연결 시도 중...")
                    if not self.connect():
                        print("[❌ 재연결 실패] 메시지 전송을 건너뜁니다.")
                        return False
                else:
                    print("[❌ 전송 실패] 최대 재시도 횟수를 초과했습니다.")
                    return False
            except Exception as e:
                print(f"[❌ 예상치 못한 오류] {e}")
                retry_count += 1
                if retry_count < max_retries:
                    if not self.connect():
                        return False
                else:
                    return False
                    
        return False
    
    # 통합 상태 업데이트 전송
    def send_status_update(self):
        """통합 상태 업데이트 전송
        
        Returns:
            bool: 전송 성공 여부
        """
        timestamp = time.time()
        
        status_payload = {
            "timestamp": timestamp,
            "battery": {
                "level": self.battery_level,
                "is_charging": self.charging
            },
            "position": {
                "current": self.current_position,
                "run_state": self.run_state
            }
        }
        
        return self.send("STATUS_UPDATE", status_payload, wait=False)
    
    # 정기적인 상태 업데이트 타이머
    def status_update_timer(self, interval=3):
        """정기적으로 상태 업데이트 전송"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.updating:
            try:
                # 배터리 상태 업데이트
                current_level = self.battery_level
                
                if self.charging:
                    self.battery_level = min(100, self.battery_level + 5)
                    print(f"[DEBUG] 배터리 충전 중: {current_level}% -> {self.battery_level}%")
                elif self.current_position == "STANDBY":
                    # STANDBY에서는 배터리 유지
                    print(f"[DEBUG] STANDBY 상태: 배터리 유지 {self.battery_level}%")
                else:
                    self.battery_level = max(0, self.battery_level - 5)
                    print(f"[DEBUG] 배터리 감소 중: {current_level}% -> {self.battery_level}% (위치: {self.current_position})")
                
                # 통합 상태 업데이트 전송
                if self.send_status_update():
                    # 성공적으로 전송했다면 에러 카운트 초기화
                    consecutive_errors = 0
                else:
                    # 상태 업데이트 전송 실패
                    consecutive_errors += 1
                    print(f"[⚠️ 상태 업데이트 실패] 연속 실패 횟수: {consecutive_errors}/{max_consecutive_errors}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print("[❌ 상태 업데이트 중단] 연속 실패 횟수가 한계를 초과했습니다. 서버 연결 상태를 확인하세요.")
                        break
                
                time.sleep(interval)
            except Exception as e:
                consecutive_errors += 1
                print(f"[ERROR] 상태 업데이트 중 오류 발생: {str(e)}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print("[❌ 상태 업데이트 중단] 연속 오류가 너무 많습니다.")
                    break
                    
                # 짧은 대기 후 재시도
                time.sleep(1)
                
                # 특정 횟수 이상 실패 시 재연결 시도
                if consecutive_errors % 3 == 0:
                    print("[🔄 재연결 시도] 연속 오류가 발생하여 서버에 재연결을 시도합니다.")
                    if not self.connect():
                        print("[⚠️ 재연결 실패] 서버에 연결할 수 없습니다.")
    
    # 미션 수신 대기
    def wait_for_mission_response(self, timeout=5.0):
        self.client.settimeout(timeout)
        try:
            while True:
                # 데이터 수신
                data = self.client.recv(4096)
                if not data:
                    print("[❌ 연결 종료] 서버와의 연결이 끊어졌습니다.")
                    self.connect()  # 재연결
                    time.sleep(1)  # 재연결 후 잠시 대기
                    return False
                raw = data.decode('utf-8').strip()  
                for line in raw.splitlines():
                    print(f"[📩 수신] {line}")
                    try:
                        msg = json.loads(line)
                        if msg.get("cmd") == "MISSION_ASSIGNED":
                            source = msg["payload"]["source"]
                            # source가 비어있는 경우 기본값 설정
                            if not source:
                                source = "LOAD_A"
                                print(f"[⚠️ 경고] 빈 source 값을 수신함 - 기본값 '{source}'을 사용합니다")
                            
                            self.source = source.upper()
                            print(f"[✅ 미션 수신] → source = {self.source}")
                            return True
                        elif msg.get("cmd") == "NO_MISSION":
                            reason = msg.get("payload", {}).get("reason", "")
                            if reason == "BATTERY_LOW" or reason == "CHARGING":
                                print(f"[🔋 충전 필요] {reason}")
                                self.charging = True  # 충전 상태로 설정
                                self.run_state = "CHARGING"
                                # 충전이 완료될 때까지 대기
                                while True:
                                    time.sleep(5)  # 5초마다 배터리 상태 확인
                                    if self.battery_level >= 100:
                                        print("[🔋 충전 완료] 충전 완료 메시지 전송")
                                        self.charging = False
                                        self.run_state = "IDLE"
                                        self.send("FINISH_CHARGING", wait=False)
                                        return self.wait_for_mission_response()
                            else:
                                print("[ℹ️ 미션 없음] 서버에서 미션이 없다고 응답함. 3초 후 재요청.")
                                time.sleep(3)
                                self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                                # 재귀적으로 다시 대기
                                return self.wait_for_mission_response()
                        elif msg.get("cmd") == "START_CHARGING":
                            print("[🔋 충전 시작] 서버로부터 충전 명령 수신")
                            self.charging = True
                            self.run_state = "CHARGING"
                            # 충전이 완료될 때까지 대기
                            while self.battery_level < 100:
                                time.sleep(1)
                            print("[🔋 충전 완료] 100% 도달")
                            self.charging = False
                            self.run_state = "IDLE"
                            self.send("FINISH_CHARGING", wait=False)
                            return self.wait_for_mission_response()
                        elif msg.get("cmd") == "CHARGING_COMPLETED":
                            print("[🔋 충전 완료 메시지 수신]")
                            self.charging = False
                            self.run_state = "IDLE"
                            # 배터리가 30% 이하일 때만 다시 충전 요청
                            if self.battery_level <= 30:
                                print(f"[🔋 배터리 부족] {self.battery_level}% - 충전 요청")
                                self.charging = True
                                self.run_state = "CHARGING"
                                self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                            else:
                                print(f"[🔋 배터리 충분] {self.battery_level}% - 미션 요청")
                                self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                            return self.wait_for_mission_response()
                        elif msg.get("cmd") == "RUN":
                            print("[ℹ️ RUN 명령 수신]")
                            self.run_state = "RUNNING"
                            continue
                        else:
                            print(f"[ℹ️ 기타 메시지] {msg}")
                    except json.JSONDecodeError:
                        print("[ℹ️ 비JSON 메시지 무시]")
                        continue
            return False
        except socket.timeout:
            print("[⏰ 타임아웃] MISSION_ASSIGNED 수신 실패")
            self.connect()  # 재연결
            time.sleep(1)  # 재연결 후 잠시 대기
            return False
        except Exception as e:
            print(f"[❌ 오류] → {e}")
            self.connect()  # 재연결
            time.sleep(1)  # 재연결 후 잠시 대기
            return False
        finally:
            self.client.settimeout(None)

    def wait_for_gate_response(self, timeout=15.0):
        """
        게이트 열림 명령을 기다립니다.
        게이트가 열리면 ACK_GATE_OPENED를 보내야 합니다.
        """
        self.client.settimeout(timeout)
        received_gate_open = False
        
        try:
            # 게이트 응답 대기 (최대 timeout 초)
            start_time = time.time()
            while time.time() - start_time < timeout:
                # 소켓에서 데이터를 읽음
                try:
                    raw = self.client.recv(4096).decode()
                    if not raw:
                        time.sleep(0.1)
                        continue
                except socket.timeout:
                    continue
                
                for line in raw.splitlines():
                    print(f"[📩 수신] {line}")
                    try:
                        msg = json.loads(line)
                        cmd = msg.get("cmd", "")
                        
                        # GATE_OPENED 명령을 받으면 성공
                        if cmd == "GATE_OPENED":
                            print("[✅ 게이트 열림 확인]")
                            received_gate_open = True
                        
                        # RUN 명령 처리
                        elif cmd == "RUN":
                            print("[ℹ️ RUN 명령 수신]")
                            self.run_state = "RUNNING"
                        
                        # GATE_CLOSED는 이전 게이트에 대한 것이므로 무시
                        elif cmd == "GATE_CLOSED":
                            continue
                            
                        else:
                            print(f"[ℹ️ 기타 메시지] {msg}")
                            
                    except json.JSONDecodeError:
                        print("[ℹ️ 비JSON 메시지 무시]")
                        continue
                
                # GATE_OPENED를 받았으면 루프 종료
                if received_gate_open:
                    return True
                
        except socket.timeout:
            print("[⏰ 타임아웃] GATE_OPENED 수신 실패")
            return False
        except Exception as e:
            print(f"[❌ 오류] → {e}")
            return False
        finally:
            self.client.settimeout(None)
        
        return received_gate_open

    def wait_for_run_command(self, timeout=5.0):
        """
        RUN 명령을 기다립니다.
        """
        self.client.settimeout(timeout)
        received_run = False
        
        try:
            print("[🔄 RUN 명령 대기 중...]")
            # RUN 명령 대기 (최대 timeout 초)
            start_time = time.time()
            while time.time() - start_time < timeout:
                # 소켓에서 데이터를 읽음
                try:
                    raw = self.client.recv(4096).decode()
                    if not raw:
                        time.sleep(0.1)
                        continue
                except socket.timeout:
                    continue
                
                for line in raw.splitlines():
                    print(f"[📩 수신] {line}")
                    try:
                        msg = json.loads(line)
                        cmd = msg.get("cmd", "")
                        
                        # RUN 명령을 받으면 성공
                        if cmd == "RUN":
                            print("[✅ RUN 명령 수신 - 이동 시작]")
                            self.run_state = "RUNNING"
                            received_run = True
                            break
                        else:
                            print(f"[ℹ️ 기타 메시지] {msg}")
                            
                    except json.JSONDecodeError:
                        print("[ℹ️ 비JSON 메시지 무시]")
                        continue
                
                # RUN을 받았으면 루프 종료
                if received_run:
                    return True
            
        except socket.timeout:
            print("[⏰ 타임아웃] RUN 명령 수신 실패")
            return False
        except Exception as e:
            print(f"[❌ 오류] → {e}")
            return False
        finally:
            self.client.settimeout(None)
        
        return received_run

    def run_full_mission(self):
        """전체 미션 절차를 수행합니다."""
        # 서버 연결 확인
        if not self.client:
            print("[⚠️ 서버 연결 없음] 연결을 시도합니다...")
            if not self.connect():
                print("[❌ 미션 취소] 서버에 연결할 수 없습니다.")
                return False
        
        try:
            # 최초 1회만 등록 및 초기화
            if not self.send("HELLO", {"msg": "register"}, wait=True):
                print("[❌ 초기화 실패] 서버에 등록할 수 없습니다.")
                return False
                
            time.sleep(0.5)
            
            # 첫 미션 요청
            print("[🔍 미션 요청] 서버에 새로운 미션을 요청합니다...")
            if not self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False):
                print("[❌ 미션 요청 실패] 서버에 미션을 요청할 수 없습니다.")
                return False
                
            mission_received = self.wait_for_mission_response()
            if not mission_received:
                print("[ℹ️ 미션 없음] 5초 후 다시 시도합니다.")
                time.sleep(5)
                return self.run_full_mission()  # 재귀 호출로 다시 시작

            # 미션 시작
            print(f"[✅ 미션 시작] 소스: {self.source}")
            
            # ✅ 전체 미션 수행
            print("\n[🚛 트럭 이동] CHECKPOINT_A로 이동 중...")
            time.sleep(2)  # 이동 시간
            self.current_position = "CHECKPOINT_A"
            self.charging = False
            
            # 도착 알림
            if not self.send("ARRIVED", {"position": "CHECKPOINT_A", "gate_id": "GATE_A"}):
                print("[❌ 도착 알림 실패] 서버에 도착 알림을 보낼 수 없습니다.")
                return False
                
            if self.wait_for_gate_response():
                if not self.send("ACK_GATE_OPENED"):
                    print("[❌ 게이트 ACK 실패] 서버에 게이트 열림 확인을 보낼 수 없습니다.")
                    return False
                    
                # RUN 명령을 기다린 후 이동
                if self.wait_for_run_command():
                    print("\n[🚛 트럭 이동] CHECKPOINT_B로 이동 중...")
                else:
                    print("[❌ 오류] RUN 명령을 받지 못했습니다.")
                    return False
            else:
                print("[❌ 오류] GATE_A가 열리지 않았습니다.")
                return False

            time.sleep(2)  # 이동 시간
            self.current_position = "CHECKPOINT_B"
            if not self.send("ARRIVED", {"position": "CHECKPOINT_B", "gate_id": "GATE_A"}):
                print("[❌ 도착 알림 실패] 서버에 도착 알림을 보낼 수 없습니다.")
                return False

            print(f"\n[🚛 트럭 이동] {self.source}로 이동 중...")
            time.sleep(2)  # 이동 시간
            self.current_position = self.source
            if not self.send("ARRIVED", {"position": self.source}):  # load_A or load_B
                print("[❌ 도착 알림 실패] 서버에 도착 알림을 보낼 수 없습니다.")
                return False

            print("\n[📦 적재 시작]")
            time.sleep(1)  # 적재 준비 시간
            self.run_state = "LOADING"
            if not self.send("START_LOADING"):
                print("[❌ 적재 시작 알림 실패] 서버에 적재 시작 알림을 보낼 수 없습니다.")
                return False
        
            # 적재 시간
            loading_time = 5
            for i in range(loading_time):
                print(f"[📦 적재 중...] {i+1}/{loading_time}")
                time.sleep(1)

            # 적재 완료
            print("[📦 적재 완료]")
            self.run_state = "LOADED"
            if not self.send("FINISH_LOADING"):
                print("[❌ 적재 완료 알림 실패] 서버에 적재 완료 알림을 보낼 수 없습니다.")
                return False

            print("\n[🚛 트럭 이동] CHECKPOINT_C로 이동 중...")
            time.sleep(2)
            self.current_position = "CHECKPOINT_C"
            if not self.send("ARRIVED", {"position": "CHECKPOINT_C", "gate_id": "GATE_B"}):
                print("[❌ 도착 알림 실패] 서버에 도착 알림을 보낼 수 없습니다.")
                return False
                
            if self.wait_for_gate_response():
                if not self.send("ACK_GATE_OPENED"):
                    print("[❌ 게이트 ACK 실패] 서버에 게이트 열림 확인을 보낼 수 없습니다.")
                    return False
                    
                # RUN 명령을 기다린 후 이동
                if self.wait_for_run_command():
                    print("\n[🚛 트럭 이동] CHECKPOINT_D로 이동 중...")
                else:
                    print("[❌ 오류] RUN 명령을 받지 못했습니다.")
                    return False
            else:
                print("[❌ 오류] GATE_B가 열리지 않았습니다.")
                return False

            time.sleep(2)  # 이동 시간
            self.current_position = "CHECKPOINT_D"
            if not self.send("ARRIVED", {"position": "CHECKPOINT_D", "gate_id": "GATE_B"}):
                print("[❌ 도착 알림 실패] 서버에 도착 알림을 보낼 수 없습니다.")
                return False

            print("\n[🚛 트럭 이동] BELT로 이동 중...")
            time.sleep(2)
            self.current_position = "BELT"
            if not self.send("ARRIVED", {"position": "BELT"}):
                print("[❌ 도착 알림 실패] 서버에 도착 알림을 보낼 수 없습니다.")
                return False

            print("\n[📦 하역 시작]")
            time.sleep(1)
            self.run_state = "UNLOADING"
            if not self.send("START_UNLOADING"):
                print("[❌ 하역 시작 알림 실패] 서버에 하역 시작 알림을 보낼 수 없습니다.")
                return False
                
            # 하역 시간
            unloading_time = 5
            for i in range(unloading_time):
                print(f"[📦 하역 중...] {i+1}/{unloading_time}")
                time.sleep(1)
                
            print("[📦 하역 완료]")
            self.run_state = "IDLE"
            if not self.send("FINISH_UNLOADING"):
                print("[❌ 하역 완료 알림 실패] 서버에 하역 완료 알림을 보낼 수 없습니다.")
                return False

            print("\n[🚛 트럭 이동] STANDBY로 이동 중...")
            time.sleep(2)
            self.current_position = "STANDBY"
            if not self.send("ARRIVED", {"position": "STANDBY"}):
                print("[❌ 도착 알림 실패] 서버에 도착 알림을 보낼 수 없습니다.")
                return False

            print(f"\n✅ 미션 완료] 배터리 잔량: {self.battery_level}%")
            if self.battery_level <= 30:
                print("[🔋 배터리 부족] 충전 후 계속")
            else:
                print("[🔋 배터리 충분] 새 미션 요청 중...")
                time.sleep(3)
                self.run_full_mission()  # 재귀 호출로 다시 시작
                
            return True
            
        except Exception as e:
            print(f"\n❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    try:
        print(f"[🚚 트럭 시뮬레이터] 서버 {HOST}:{PORT}에 연결을 시도합니다...")
        print(f"[ℹ️ 참고] 서버가 실행 중이 아니라면 먼저 'python run/run_main_server.py'를 실행하세요.")
        
        # 서버 연결 테스트
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(2.0)
        try:
            test_socket.connect((HOST, PORT))
            print(f"[✅ 서버 연결 성공] 서버 {HOST}:{PORT}가 응답합니다.")
            test_socket.close()
        except (ConnectionRefusedError, socket.timeout):
            print(f"[❌ 서버 연결 실패] 서버 {HOST}:{PORT}에 연결할 수 없습니다.")
            print(f"[ℹ️ 해결 방법] 먼저 'python run/run_main_server.py'를 실행하여 서버를 시작하세요.")
            print(f"[ℹ️ 해결 방법] 또는 이미 실행 중인 서버 프로세스를 종료하고 다시 시작해보세요.")
            print(f"[ℹ️ 서버 프로세스 종료 방법] 'pkill -f run_main_server.py' 명령어로 기존 서버를 종료할 수 있습니다.")
            sys.exit(1)
        
        # 시뮬레이터 시작
        simulator = TruckSimulator()
        
        # 미션 바로 시작
        print("[🚚 미션 시작] 서버에 미션을 요청합니다...")
        simulator.run_full_mission()
        
    except KeyboardInterrupt:
        print("\n[👋 종료] 사용자에 의해 시뮬레이터가 종료되었습니다.")
    except Exception as e:
        print(f"\n[❌ 오류] 시뮬레이터에서 예상치 못한 오류가 발생했습니다: {e}")
        import traceback
        traceback.print_exc()
