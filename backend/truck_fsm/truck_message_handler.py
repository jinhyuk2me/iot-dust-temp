# backend/truck_fsm/truck_message_handler.py

from typing import TYPE_CHECKING
import time
from .truck_state_enum import TruckState

if TYPE_CHECKING:
    from .truck_fsm_manager import TruckFSMManager
    from ..truck_status.truck_status_manager import TruckStatusManager


class TruckMessageHandler:
    def __init__(self, truck_fsm_manager: 'TruckFSMManager'):
        self.truck_fsm_manager = truck_fsm_manager
        self.truck_status_manager = None

    def set_status_manager(self, truck_status_manager: 'TruckStatusManager'):
        self.truck_status_manager = truck_status_manager

    def handle_message(self, msg: dict):
        sender = msg.get("sender")
        cmd = msg.get("cmd", "").strip().upper()
        payload = msg.get("payload", {})

        print(f"[📨 TruckMessageHandler] sender={sender}, cmd={cmd}")

        # 트럭 상태 업데이트
        if self.truck_status_manager and cmd == "STATUS_UPDATE":
            self._handle_status_update(sender, payload)
            return
        
        # ACK_GATE_OPENED는 우선 처리
        if cmd == "ACK_GATE_OPENED":
            self.truck_fsm_manager.handle_trigger(sender, "ACK_GATE_OPENED", payload)
            return

        # FSM 트리거 처리
        self.truck_fsm_manager.handle_trigger(sender, cmd, payload)

        if not sender:
            print("[MessageHandler] sender가 없음")
            return

        if cmd == "ARRIVED":
            position = payload.get("position", "UNKNOWN")
            gate_id = payload.get("gate_id", "")
            
            # 현재 FSM 상태 저장
            current_fsm_state = self.truck_fsm_manager.get_state(sender)
            print(f"[📍 위치 도착] {sender}가 {position}에 도착 (게이트: {gate_id}, FSM 상태: {current_fsm_state})")
            
            # 위치 정보만 업데이트 (FSM 상태는 변경하지 않음)
            if self.truck_status_manager:
                # 위치 정보만 업데이트 (run_state는 "ARRIVED"로 설정하지 않음)
                self.truck_status_manager.update_position(sender, position, "IDLE")  # 도착 시 IDLE 상태로 설정
            
            # ARRIVED_AT_ 형식의 트리거 생성 (이 트리거가 FSM 상태를 변경할 것임)
            trigger = f"ARRIVED_AT_{position.upper()}"
            print(f"[🔄 트리거 생성] {trigger} (현재 FSM 상태: {current_fsm_state})")
            self.truck_fsm_manager.handle_trigger(sender, trigger, payload)

        elif cmd == "OBSTACLE":
            self.truck_fsm_manager.handle_trigger(sender, "OBSTACLE", payload)

        elif cmd == "ERROR":
            self.truck_fsm_manager.handle_trigger(sender, "EMERGENCY_TRIGGERED", payload)

        elif cmd == "RESET":
            self.truck_fsm_manager.handle_trigger(sender, "RESET", payload)

        elif cmd == "ASSIGN_MISSION":
            self.truck_fsm_manager.handle_trigger(sender, "ASSIGN_MISSION", payload)

        elif cmd == "START_LOADING":
            self.truck_fsm_manager.handle_trigger(sender, "START_LOADING", payload)

        elif cmd == "FINISH_LOADING":
            self.truck_fsm_manager.handle_trigger(sender, "FINISH_LOADING", payload)

        elif cmd == "START_UNLOADING":
            self.truck_fsm_manager.handle_trigger(sender, "START_UNLOADING", payload)

        elif cmd == "FINISH_UNLOADING":
            self.truck_fsm_manager.handle_trigger(sender, "FINISH_UNLOADING", payload)

        elif cmd == "FINISH_CHARGING":
            self.truck_fsm_manager.handle_trigger(sender, "FINISH_CHARGING", payload)
            return

        elif cmd == "HELLO":
            # HELLO 명령은 트럭 등록을 위한 초기 명령이므로 무시
            print(f"[MessageHandler] 트럭 등록 확인: {sender}")
            return

        else:
            print(f"[MessageHandler] 알 수 없는 명령: {cmd}")
            
    def _handle_status_update(self, truck_id: str, payload: dict):
        """
        STATUS_UPDATE 명령 처리
        
        Args:
            truck_id (str): 트럭 ID
            payload (dict): 상태 정보를 담은 페이로드
        """
        # 타임스탬프 확인
        timestamp = payload.get("timestamp", time.time())
        
        # 배터리 상태 업데이트
        battery_data = payload.get("battery", {})
        if battery_data:
            level = battery_data.get("level", 0)
            is_charging = battery_data.get("is_charging", False)
            self.truck_status_manager.update_battery(truck_id, level, is_charging)
            
            # 배터리가 100%이고 충전 중이면 자동으로 충전 완료 처리
            if level >= 100 and is_charging:
                print(f"[🔋 자동 충전 완료] {truck_id}의 배터리가 100%에 도달했습니다. 충전 상태를 해제합니다.")
                self.truck_status_manager.update_battery(truck_id, level, False)
                # 현재 FSM 상태가 CHARGING이면 FINISH_CHARGING 트리거 발생
                current_fsm_state = self.truck_fsm_manager.get_state(truck_id)
                if str(current_fsm_state) == "TruckState.CHARGING" or current_fsm_state.name == "CHARGING":
                    self.truck_fsm_manager.handle_trigger(truck_id, "FINISH_CHARGING", {})
        
        # 위치 정보 업데이트
        position_data = payload.get("position", {})
        if position_data:
            # current 또는 location 키로 위치 데이터 가져오기
            location = position_data.get("current", position_data.get("location", "UNKNOWN"))
            # run_state 또는 status 키로 상태 데이터 가져오기
            run_state = position_data.get("run_state", position_data.get("status", "IDLE"))
            
            print(f"[DEBUG] 위치 업데이트: {truck_id} - location={location}, status={run_state}")
            
            # 현재 FSM 상태를 가져와서 보존
            current_fsm_state = self.truck_fsm_manager.get_state(truck_id)
            print(f"[DEBUG] 현재 FSM 상태: {current_fsm_state}")
            
            # 위치와 상태 모두 업데이트 (FSM 상태는 건드리지 않음)
            self.truck_status_manager.update_position(truck_id, location, run_state)
            
            # 현재 위치에 따라 트리거 생성 (위치 업데이트 중에는 FSM 상태를 변경하지 않기 위함)
            if location and location != "UNKNOWN":
                # 비정상적인 경로 감지
                if self._is_abnormal_path(run_state, location):
                    print(f"[⚠️ 경로 이상 감지] {truck_id}가 {run_state} 상태에서 {location}에 비정상적으로 도착")
                
                trigger = f"ARRIVED_AT_{location.upper()}"
                print(f"[DEBUG] 위치 기반 트리거: {trigger} (FSM 상태: {current_fsm_state})")
            
            # run_state에 따른 추가 트리거 처리
            if run_state in ["LOADING", "UNLOADING"]:
                print(f"[DEBUG] 작업 상태 감지: {run_state}")
                current_fsm_state_name = current_fsm_state.name if hasattr(current_fsm_state, 'name') else str(current_fsm_state)
                
                if run_state == "LOADING":
                    # 로딩 중인지 확인 - FSM 상태 이름 기반으로 비교
                    loading_states = ["LOADING", "WAIT_LOAD"]
                    if current_fsm_state_name not in loading_states:
                        print(f"[DEBUG] LOADING 상태 트리거 생성 (FSM 상태: {current_fsm_state_name})")
                        self.truck_fsm_manager.handle_trigger(truck_id, "START_LOADING", {})
                
                elif run_state == "UNLOADING":
                    # 언로딩 중인지 확인 - FSM 상태 이름 기반으로 비교
                    unloading_states = ["UNLOADING", "WAIT_UNLOAD"]
                    if current_fsm_state_name not in unloading_states:
                        print(f"[DEBUG] UNLOADING 상태 트리거 생성 (FSM 상태: {current_fsm_state_name})")
                        self.truck_fsm_manager.handle_trigger(truck_id, "START_UNLOADING", {})
                
        print(f"[✅ 상태 업데이트 완료] {truck_id}: {payload}")
        
    def _is_abnormal_path(self, current_state: str, position: str) -> bool:
        """
        비정상적인 경로인지 감지
        
        Args:
            current_state (str): 현재 트럭 상태
            position (str): 도착한 새 위치
            
        Returns:
            bool: 비정상 경로면 True, 정상이면 False
        """
        # MOVE_TO_LOAD 상태에서 CHECKPOINT_C에 도착하는 것은 비정상
        if "MOVE_TO_LOAD" in current_state and position == "CHECKPOINT_C":
            return True
            
        # MOVE_TO_LOAD 상태에서 STANDBY에 도착하는 것은 비정상
        if "MOVE_TO_LOAD" in current_state and position == "STANDBY":
            return True
            
        # 나머지 경우는 정상
        return False