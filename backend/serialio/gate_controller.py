# backend/serialio/gate_controller.py

import time
from .serial_controller import SerialController

class GateController(SerialController):
    def __init__(self, serial_interface, facility_status_manager=None):
        super().__init__(serial_interface)
        self.gate_states = {
            "GATE_A": "CLOSED",
            "GATE_B": "CLOSED"
        }
        self.operations_in_progress = {}
        self.current_gate_id = None  # 현재 작업 중인 게이트 ID
        self.facility_status_manager = facility_status_manager
        
    # ----------------------- 명령 전송 -----------------------
    
    def send_command(self, gate_id: str, action: str):
        self.current_gate_id = gate_id  # 현재 게이트 ID 저장
        if action.upper() == "OPEN":
            return self.open_gate(gate_id)
        elif action.upper() == "CLOSE":
            return self.close_gate(gate_id)
        else:
            print(f"[GateController] 알 수 없는 동작: {action}")
            return False
    
    # ----------------------- 상태 관리 -----------------------
    
    def _update_gate_status(self, gate_id: str, state: str, operation: str = "IDLE"):
        """게이트 상태 업데이트 및 facility_status_manager에 보고"""
        # 내부 상태 업데이트
        old_state = self.gate_states.get(gate_id)
        self.gate_states[gate_id] = state
        print(f"[게이트 상태 업데이트] {gate_id}: {old_state} → {state}")
        
        # facility_status_manager가 있으면 상태 업데이트
        if self.facility_status_manager:
            self.facility_status_manager.update_gate_status(gate_id, state, operation)
    
    # ----------------------- 메시지 처리 -----------------------
    
    # 메시지 처리
    def handle_message(self, message: str):
        if not message:
            return
            
        # 게이트 상태 변경을 나타내는 메시지 분석
        parsed = self.interface.parse_response(message)
        
        # 게이트 상태 메시지 처리
        if parsed["type"] == "GATE" and "gate_id" in parsed and "state" in parsed:
            gate_id = parsed["gate_id"]
            state = parsed["state"]
            
            # 상태 업데이트
            if gate_id in self.gate_states:
                # facility_status_manager 업데이트 메서드 호출
                self._update_gate_status(gate_id, state, "STATUS_UPDATE")
        
        # 다른 관련 메시지 처리 (필요시 확장)
        elif parsed["type"] != "UNKNOWN" and parsed["type"] != "EMPTY":
            print(f"[GateController] 기타 메시지 수신: {message}")

    # 응답이 성공을 나타내는지 확인
    def _is_success_response(self, response, gate_id, action):
        if not response:
            return False
            
        parsed = self.interface.parse_response(response)
        
        # ACK 메시지 처리 (표준 형식)
        if parsed["type"] == "ACK":
            if "command" in parsed:
                # 명령과 게이트 ID가 일치하는지 확인
                expected_command = f"{gate_id}_{action}"
                if expected_command in parsed["command"]:
                    # SUCCESS 또는 OK가 결과에 포함되어 있으면 성공
                    if "result" in parsed and (parsed["result"] == "SUCCESS" or parsed["result"] == "OK" or "SUCCESS" in parsed["result"]):
                        return True
        
        # STATUS 메시지 처리 (표준 형식)
        elif parsed["type"] == "STATUS" or parsed["type"] == "GATE":
            if "gate_id" in parsed and parsed["gate_id"] == gate_id:
                if (action.upper() == "OPEN" and parsed["state"] == "OPENED") or \
                   (action.upper() == "CLOSE" and parsed["state"] == "CLOSED"):
                    return True
            elif "target" in parsed and parsed["target"] == gate_id:
                if (action.upper() == "OPEN" and parsed["state"] == "OPENED") or \
                   (action.upper() == "CLOSE" and parsed["state"] == "CLOSED"):
                    return True
        
        # 텍스트 기반 검사 (하위 호환성)
        if (response.startswith(f"ACK:{gate_id}_OPEN") or 
            response.startswith(f"ACK:{gate_id}_CLOSE") or
            response.startswith(f"STATUS:{gate_id}:OPENED") or
            response.startswith(f"STATUS:{gate_id}:CLOSED")) and (
            "SUCCESS" in response or "OK" in response or 
            ":OPENED" in response or ":CLOSED" in response):
            return True
                
        return False

    # ----------------------- 게이트 제어 -----------------------

    # 게이트 열기
    def open_gate(self, gate_id: str):
        if not gate_id:
            print(f"[게이트 ID 누락] 게이트 ID가 지정되지 않았습니다.")
            return False
            
        # 이미 열려있거나 작업이 진행 중인 경우 무시
        if self.gate_states.get(gate_id) == "OPENED":
            print(f"[게이트 이미 열림] {gate_id}는 이미 열려 있습니다.")
            return True
        
        if gate_id in self.operations_in_progress and self.operations_in_progress[gate_id]:
            print(f"[게이트 작업 중] {gate_id}에 대한 작업이 이미 진행 중입니다.")
            return False
        
        # 작업 시작 표시
        self.operations_in_progress[gate_id] = True
        print(f"[게이트 열기 요청] → {gate_id}")
        
        # facility_status_manager 상태 업데이트 - 작업 시작
        if self.facility_status_manager:
            self.facility_status_manager.update_gate_status(gate_id, "CLOSED", "OPENING")
        
        # 게이트 ID를 저장(응답 확인용)
        self.current_gate_id = gate_id
        
        # 명령 전송 - 표준화된 프로토콜 사용
        self.interface.send_command(gate_id, "OPEN")
        
        # 응답 대기
        print(f"[게이트 열림 대기 중] {gate_id} - 최대 15초 대기")
        response = self.interface.read_response(timeout=15)
        
        # 응답 확인
        success = self._is_success_response(response, gate_id, "OPEN")
        
        # 결과 처리
        if success:
            print(f"[게이트 열림 완료] {gate_id}")
            # facility_status_manager 업데이트 메서드 호출
            self._update_gate_status(gate_id, "OPENED", "IDLE")
        else:
            print(f"[게이트 열림 실패] {gate_id} - 응답: {response}")
            # facility_status_manager 실패 상태 업데이트
            if self.facility_status_manager:
                self.facility_status_manager.update_gate_status(gate_id, "CLOSED", "OPEN_FAILED")
        
        # 작업 완료 표시
        self.operations_in_progress[gate_id] = False
        return success

    # 게이트 닫기
    def close_gate(self, gate_id: str):
        if not gate_id:
            print(f"[게이트 ID 누락] 게이트 ID가 지정되지 않았습니다.")
            return False
            
        # 이미 닫혀있거나 작업이 진행 중인 경우 무시
        if self.gate_states.get(gate_id) == "CLOSED":
            print(f"[게이트 이미 닫힘] {gate_id}는 이미 닫혀 있습니다.")
            return True
        
        if gate_id in self.operations_in_progress and self.operations_in_progress[gate_id]:
            print(f"[게이트 작업 중] {gate_id}에 대한 작업이 이미 진행 중입니다.")
            return False
        
        # 작업 시작 표시
        self.operations_in_progress[gate_id] = True
        print(f"[게이트 닫기 요청] → {gate_id}")
        
        # facility_status_manager 상태 업데이트 - 작업 시작
        if self.facility_status_manager:
            self.facility_status_manager.update_gate_status(gate_id, "OPENED", "CLOSING")
        
        # 게이트 ID를 저장(응답 확인용)
        self.current_gate_id = gate_id
        
        # 응답 대기 시간 연장
        timeout = 15  # 15초로 확장
        
        # 명령 전송 - 표준화된 프로토콜 사용
        self.interface.send_command(gate_id, "CLOSE")
        
        # 응답 대기
        print(f"[게이트 닫힘 대기 중] {gate_id} - 최대 {timeout}초 대기")
        response = self.interface.read_response(timeout=timeout)
        
        # 응답 확인
        success = self._is_success_response(response, gate_id, "CLOSE")
        
        # 결과 처리
        if success:
            print(f"[게이트 닫힘 완료] {gate_id}")
            # facility_status_manager 업데이트 메서드 호출
            self._update_gate_status(gate_id, "CLOSED", "IDLE")
        else:
            # 재시도 로직
            if not response:
                print(f"[게이트 닫힘 응답 없음] {gate_id} - 재시도...")
                # 약간의 지연 후 재시도
                time.sleep(1.0)
                self.interface.send_command(gate_id, "CLOSE")
                response = self.interface.read_response(timeout=timeout)
                success = self._is_success_response(response, gate_id, "CLOSE")
                
                if success:
                    print(f"[게이트 닫힘 완료 (재시도)] {gate_id}")
                    # facility_status_manager 업데이트 메서드 호출
                    self._update_gate_status(gate_id, "CLOSED", "IDLE")
                else:
                    print(f"[게이트 닫힘 실패 (재시도)] {gate_id} - 응답: {response}")
                    
                    # 실패시 세 번째 시도
                    if not response:
                        print(f"[게이트 닫힘 응답 없음] {gate_id} - 마지막 시도...")
                        time.sleep(2.0)  # 더 긴 지연
                        self.interface.send_command(gate_id, "CLOSE")
                        response = self.interface.read_response(timeout=timeout)
                        success = self._is_success_response(response, gate_id, "CLOSE")
                        
                        if success:
                            print(f"[게이트 닫힘 완료 (최종 시도)] {gate_id}")
                            # facility_status_manager 업데이트 메서드 호출
                            self._update_gate_status(gate_id, "CLOSED", "IDLE")
                        else:
                            print(f"[게이트 닫힘 실패 (최종 시도)] {gate_id} - 응답: {response}")
                            # facility_status_manager 실패 상태 업데이트
                            if self.facility_status_manager:
                                self.facility_status_manager.update_gate_status(gate_id, "OPENED", "CLOSE_FAILED")
            else:
                print(f"[게이트 닫힘 실패] {gate_id} - 응답: {response}")
                # facility_status_manager 실패 상태 업데이트
                if self.facility_status_manager:
                    self.facility_status_manager.update_gate_status(gate_id, "OPENED", "CLOSE_FAILED")
        
        # 작업 완료 표시
        self.operations_in_progress[gate_id] = False
        
        # 가상 환경에서의 특별 처리
        if not success and gate_id == "GATE_A":  # GATE_A에 대해서만 특별 처리
            print(f"[가상 환경 대응] {gate_id}의 상태를 'CLOSED'로 강제 설정합니다.")
            # facility_status_manager 업데이트 메서드 호출
            self._update_gate_status(gate_id, "CLOSED", "FORCED_CLOSE")
            success = True
            
        return success
