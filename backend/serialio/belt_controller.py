# backend/serialio/belt_controller.py

import time
import threading
from .serial_controller import SerialController

class BeltController(SerialController):
    def __init__(self, serial_interface, facility_status_manager=None):
        super().__init__(serial_interface)
        self.duration = 20
        self.belt_on = False
        self.is_full = False
        self.lock = threading.Lock()
        self.timer_thread = None
        self.container_full = False
        self.facility_status_manager = facility_status_manager

    # ----------------------- 로그 및 보고 -----------------------

    # 로그 출력
    def log(self, msg):
        print(f"[Belt] {msg}")
        
    # 상태 업데이트
    def _update_belt_status(self, state, operation, container_state="UNKNOWN"):
        """벨트 상태 업데이트 및 facility_status_manager에 보고"""
        if self.facility_status_manager:
            self.facility_status_manager.update_belt_status("BELT", state, operation, container_state)
        self.log(f"상태 업데이트: {state}, 동작: {operation}, 컨테이너: {container_state}")

    # 벨트 상태 보고
    def report_status(self, status_type, target, state):
        try:
            msg = f"{status_type}:{target}:{state}"
            self.interface.write(msg)
            self.log(f"[보고] {msg}")
            
            # BELT 상태 보고인 경우 facility_status_manager에도 보고
            if target == "BELT" and status_type == "STATUS":
                container_state = "EMPTY" if not self.container_full else "FULL"
                self._update_belt_status(state, "STATUS_REPORT", container_state)
        except Exception as e:
            self.log(f"[보고 오류] {e}")

    # ----------------------- 명령 및 응답 -----------------------

    def send_command(self, belt_id: str, action: str):
        # 벨트 작동 명령인데 컨테이너가 가득 찬 경우 거부
        if action.upper() == "RUN" and self.container_full:
            print("[벨트 작동 거부] 컨테이너가 가득 찼습니다.")
            if self.facility_status_manager:
                self._update_belt_status("STOPPED", "REJECTED", "FULL")
            return False
            
        print(f"[BeltController] 명령 전송: {belt_id}_{action}")
        
        # 명령 동작에 따른 상태 업데이트
        if action.upper() == "RUN":
            self._update_belt_status("RUNNING", "COMMAND_SENT", "EMPTY" if not self.container_full else "FULL")
        elif action.upper() == "STOP":
            self._update_belt_status("STOPPED", "COMMAND_SENT", "EMPTY" if not self.container_full else "FULL")
        elif action.upper() == "EMRSTOP":
            self._update_belt_status("EMERGENCY_STOP", "COMMAND_SENT", "EMPTY" if not self.container_full else "FULL")
        
        # 표준화된 형식으로 명령 전송
        self.interface.send_command(belt_id, action)
        return True

    # ----------------------- 메시지 처리 -----------------------

    # 메시지 처리
    def handle_message(self, message: str):
        if not message:
            return
            
        # 메시지 파싱
        parsed = self.interface.parse_response(message)
        
        # 메시지 타입별 처리
        if parsed["type"] == "BELT":
            if parsed["state"] == "RUNNING":
                if not self.is_full:
                    self.log("벨트 작동 시작 명령 수신")
                    self.turn_on_belt()
                    # 상태 업데이트
                    self._update_belt_status("RUNNING", "AUTO_START", "EMPTY")
                else:
                    self.log("무시됨: 컨테이너 A_FULL 상태")
                    # 상태 업데이트
                    self._update_belt_status("STOPPED", "REJECTED", "FULL")
            elif parsed["state"] in ["STOPPED", "EMERGENCY_STOP"]:
                self.log(f"벨트 정지 명령 수신 ({parsed['state']})")
                self.turn_off_belt()
                # 상태 업데이트
                self._update_belt_status(parsed["state"], "AUTO_STOP", "EMPTY" if not self.container_full else "FULL")
        
        elif parsed["type"] == "CONTAINER":
            container_id = parsed.get("id", "A")  # 기본값 A
            container_state = parsed.get("state", "")
            
            if container_state == "FULL":
                self.log(f"컨테이너 {container_id} 가득 참 상태 수신")
                self.is_full = True
                self.container_full = True
                self.turn_off_belt()
                # 상태 업데이트
                self._update_belt_status("STOPPED", "CONTAINER_FULL", "FULL")
            elif container_state == "EMPTY":
                self.log(f"컨테이너 {container_id} 비어있음 상태 수신")
                if container_id == "A":  # 주요 컨테이너가 비워진 경우
                    self.container_full = False
                    self.is_full = False
                    # 상태 업데이트
                    self._update_belt_status("STOPPED", "CONTAINER_EMPTIED", "EMPTY")
        
        elif parsed["type"] == "SYSTEM" and parsed["state"] == "ALL_FULL":
            # 모든 컨테이너 가득 참
            self.log("모든 컨테이너 가득 참 상태")
            self.is_full = True
            self.container_full = True
            self.turn_off_belt()
            # 상태 업데이트
            self._update_belt_status("STOPPED", "ALL_CONTAINERS_FULL", "FULL")
        
        elif parsed["type"] == "UNKNOWN":
            # 알 수 없는 명령
            self.log(f"[무시됨] 알 수 없는 메시지: {parsed['raw']}")

    # ----------------------- 응답 처리 -----------------------

    # 응답 처리
    def handle_response(self, response: str) -> bool:
        if not response:
            return False
            
        parsed = self.interface.parse_response(response)
        
        if parsed["type"] == "CONTAINER" and parsed["state"] == "FULL":
            container_id = parsed.get("id", "A")
            self.container_full = True
            print(f"[컨테이너 상태] 컨테이너 {container_id} 가득 참")
            # 상태 업데이트
            self._update_belt_status("STOPPED", "CONTAINER_FULL_RESPONSE", "FULL")
            return True
        
        elif parsed["type"] == "BELT":
            if parsed["state"] == "RUNNING":
                print("[벨트 상태] 작동 중")
                # 상태 업데이트
                self._update_belt_status("RUNNING", "STATUS_RESPONSE", "EMPTY" if not self.container_full else "FULL")
                return True
            elif parsed["state"] == "STOPPED":
                print("[벨트 상태] 정지")
                # 상태 업데이트
                self._update_belt_status("STOPPED", "STATUS_RESPONSE", "EMPTY" if not self.container_full else "FULL")
                return True
            elif parsed["state"] == "EMERGENCY_STOP":
                print("[벨트 상태] 비상 정지")
                # 상태 업데이트
                self._update_belt_status("EMERGENCY_STOP", "STATUS_RESPONSE", "EMPTY" if not self.container_full else "FULL")
                return True
            elif "route" in parsed:
                print(f"[벨트 경로] 경로 {parsed['route']}")
                return True
        
        elif parsed["type"] == "SYSTEM" and parsed["state"] == "ALL_FULL":
            print("[시스템 상태] 모든 컨테이너 가득 참")
            self.container_full = True
            # 상태 업데이트
            self._update_belt_status("STOPPED", "ALL_CONTAINERS_FULL_RESPONSE", "FULL")
            return True
            
        elif parsed["type"] == "ACK":
            command = parsed.get('command', '')
            result = parsed.get('result', '')
            print(f"[명령 응답] {command}: {result}")
            
            # BELT 관련 명령 응답 처리
            if "BELT" in command and ("SUCCESS" in result or "OK" in result):
                if "RUN" in command:
                    self.belt_on = True
                    print("[벨트 상태] 작동 중 (명령 응답)")
                    # 상태 업데이트
                    self._update_belt_status("RUNNING", "COMMAND_SUCCESS", "EMPTY" if not self.container_full else "FULL")
                elif "STOP" in command or "OFF" in command:
                    self.belt_on = False
                    print("[벨트 상태] 정지 (명령 응답)")
                    # 상태 업데이트
                    self._update_belt_status("STOPPED", "COMMAND_SUCCESS", "EMPTY" if not self.container_full else "FULL")
                elif "EMRSTOP" in command:
                    self.belt_on = False
                    print("[벨트 상태] 비상 정지 (명령 응답)")
                    # 상태 업데이트
                    self._update_belt_status("EMERGENCY_STOP", "COMMAND_SUCCESS", "EMPTY" if not self.container_full else "FULL")
            return True
        
        return False

    # ----------------------- 벨트 제어 -----------------------

    def turn_on_belt(self):
        with self.lock:
            if self.belt_on:
                self.log("이미 가동 중")
                return

            self.belt_on = True
            self.log("모터 ON → 벨트 가동 시작")
            # 상태 업데이트
            self._update_belt_status("RUNNING", "TURN_ON", "EMPTY" if not self.container_full else "FULL")
            # 표준화된 형식으로 명령 전송
            self.send_command("BELT", "RUN")

            self.timer_thread = threading.Thread(target=self._auto_off_timer)
            self.timer_thread.start()

    def turn_off_belt(self):
        with self.lock:
            if not self.belt_on:
                return
            self.belt_on = False
            self.log("모터 OFF → 벨트 정지")
            # 상태 업데이트
            self._update_belt_status("STOPPED", "TURN_OFF", "EMPTY" if not self.container_full else "FULL")
            # 표준화된 형식으로 명령 전송
            self.send_command("BELT", "STOP")

    def _auto_off_timer(self):
        time.sleep(self.duration)
        self.turn_off_belt()

    # ----------------------- 확장 메서드 -----------------------
    
    def close(self):
        self.log("벨트 컨트롤러 종료 요청")
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=1)
        super().close()  # 상위 클래스의 close 호출
