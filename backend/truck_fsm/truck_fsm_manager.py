# backend/truck_fsm/truck_fsm_manager.py

from .truck_state_enum import TruckState
from ..mission.mission_status import MissionStatus
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..tcpio.truck_command_sender import TruckCommandSender
from datetime import datetime
from ..truck_status.truck_status_manager import TruckStatusManager


class TruckFSMManager:
    def __init__(self, gate_controller, mission_manager, belt_controller=None, truck_status_manager=None):
        self.gate_controller = gate_controller
        self.mission_manager = mission_manager
        self.belt_controller = belt_controller
        self.truck_status_manager = truck_status_manager
        self.command_sender = None
        self.BATTERY_THRESHOLD = 30
        self.BATTERY_FULL = 100

    # -------------------------------- 기본 설정 --------------------------------

    def set_commander(self, commander: 'TruckCommandSender'):
        """명령 전송 객체 설정"""
        self.command_sender = commander

    def get_state(self, truck_id):
        """트럭 상태 조회"""
        if self.truck_status_manager:
            # TruckStatusManager의 새로운 FSM 상태 관리 방식 사용
            fsm_state_str = self.truck_status_manager.get_fsm_state(truck_id)
            try:
                return TruckState[fsm_state_str]
            except (KeyError, ValueError):
                # 유효하지 않은 상태 문자열인 경우 기본값 반환
                print(f"[DEBUG] 유효하지 않은 FSM 상태 문자열: {fsm_state_str}, 기본값 IDLE로 설정")
                return TruckState.IDLE
        return TruckState.IDLE

    def set_state(self, truck_id, new_state):
        """트럭 상태 설정"""
        if self.truck_status_manager:
            prev = self.get_state(truck_id)
            
            # FSM 상태만 업데이트 (트럭의 run_state나 position은 변경하지 않음)
            state_str = new_state.name if hasattr(new_state, 'name') else str(new_state)
            self.truck_status_manager.set_fsm_state(truck_id, state_str)
            print(f"[FSM] {truck_id}: {prev} → {new_state}")

    # -------------------------------- 명령 전송 --------------------------------

    def send_run(self, truck_id):
        """트럭 주행 명령 전송"""
        if self.command_sender:
            self.command_sender.send(truck_id, "RUN")

    def send_stop(self, truck_id):
        """트럭 정지 명령 전송"""
        if self.command_sender:
            self.command_sender.send(truck_id, "STOP")

    # -------------------------------- 게이트 제어 --------------------------------

    def _open_gate_and_log(self, gate_id: str, truck_id: str):
        """게이트 열림 로깅 및 명령 전송"""
        success = self.gate_controller.open_gate(gate_id)
        if success:
            print(f"[🔓 GATE OPEN] {gate_id} ← by {truck_id}")
            if self.command_sender:
                self.command_sender.send(truck_id, "GATE_OPENED", {"gate_id": gate_id})
        return success

    def _close_gate_and_log(self, gate_id: str, truck_id: str):
        """게이트 닫기 로깅 및 명령 전송"""
        success = self.gate_controller.close_gate(gate_id)
        if success:
            print(f"[🔒 GATE CLOSE] {gate_id} ← by {truck_id}")
            if self.command_sender:
                self.command_sender.send(truck_id, "GATE_CLOSED", {"gate_id": gate_id})
        return success

    # -------------------------------- 배터리 관리 --------------------------------
    
    def check_battery(self, truck_id: str) -> bool:
        """배터리 상태 확인"""
        if self.truck_status_manager:
            truck_status = self.truck_status_manager.get_truck_status(truck_id)
            battery_level = truck_status['battery']['level']
            is_charging = truck_status['battery']['is_charging']
            
            print(f"[🔋 배터리 체크] {truck_id}의 배터리: {battery_level}% (충전중: {is_charging})")
            
            # 배터리가 임계값 이하이고 충전 중이 아닌 경우
            if battery_level <= self.BATTERY_THRESHOLD and not is_charging:
                print(f"[⚠️ 경고] {truck_id}의 배터리가 낮음: {battery_level}% <= {self.BATTERY_THRESHOLD}%")
                return False
                
            # 배터리가 100%이고 충전 중인 경우 - 충전 상태 해제
            if battery_level >= self.BATTERY_FULL and is_charging:
                print(f"[✅ 완료] {truck_id}의 배터리 충전 완료: {battery_level}%")
                self.truck_status_manager.update_battery(truck_id, battery_level, False)
                # 충전 완료 트리거 발생
                print(f"[🔋 충전 완료] {truck_id}의 충전이 완료되었습니다. FINISH_CHARGING 트리거 발생")
                self.handle_trigger(truck_id, "FINISH_CHARGING", {})
                
            return True
        return False

    # -------------------------------- 트리거 처리 --------------------------------

    def handle_trigger(self, truck_id, cmd, payload):
        """트리거에 따른 FSM 상태 변경 처리"""
        try:
            state = self.get_state(truck_id)
            
            # 트럭의 현재 위치 정보를 로그
            if cmd.startswith("ARRIVED_AT_"):
                position = cmd.replace("ARRIVED_AT_", "")
                print(f"[DEBUG] 트럭 {truck_id}가 {position}에 도착, 현재 FSM 상태: {state}")
                
                # MOVE_TO_GATE_FOR_LOAD 상태가 아닌데 CHECKPOINT_A에 도착한 경우
                if position == "CHECKPOINT_A" and state != TruckState.MOVE_TO_GATE_FOR_LOAD:
                    print(f"[DEBUG] 트럭이 미션 실행 중이 아닌데 CHECKPOINT_A에 도착함 - 상태 업데이트 필요")
                    # 트럭에 할당된 미션이 있는지 확인
                    missions = self.mission_manager.get_assigned_missions_by_truck(truck_id)
                    if missions:
                        print(f"[DEBUG] 미션이 할당되어 있음: {missions[0].mission_id} - FSM 상태를 MOVE_TO_GATE_FOR_LOAD로 업데이트")
                        self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_LOAD)
                        state = TruckState.MOVE_TO_GATE_FOR_LOAD  # 상태 업데이트
            
            print(f"[FSM] 트리거: {truck_id}, 상태={state}, 트리거={cmd}")

            # IDLE 상태에서 미션 할당
            if (state == TruckState.IDLE or state == TruckState.WAIT_NEXT_MISSION) and cmd == "ASSIGN_MISSION":
                print("[DEBUG] ASSIGN_MISSION: 대기 중인 미션 확인")
                
                # 다음 미션 존재 여부 확인
                waiting_missions = self.mission_manager.get_waiting_missions()
                has_next_mission = len(waiting_missions) > 0
                print(f"[DEBUG] 대기 중인 미션 수: {len(waiting_missions)}")
                
                # 배터리 레벨 확인
                if not payload or 'battery_level' not in payload:
                    # status_manager에서 배터리 정보 확인
                    if self.truck_status_manager:
                        truck_status = self.truck_status_manager.get_truck_status(truck_id)
                        battery_level = truck_status["battery"]["level"]
                        print(f"[🔋 배터리 체크] {truck_id}의 배터리: {battery_level}% (status_manager에서 조회)")
                    else:
                        print(f"[⚠️ 경고] {truck_id}의 배터리 정보가 없음 - 충전 필요")
                        self.set_state(truck_id, TruckState.CHARGING)
                        if self.command_sender:
                            self.command_sender.send(truck_id, "START_CHARGING", {})
                        return
                else:
                    battery_level = payload['battery_level']
                    print(f"[🔋 배터리 체크] {truck_id}의 배터리: {battery_level}% (payload에서 조회)")
                
                if has_next_mission:
                    next_mission = waiting_missions[0]
                    print(f"[DEBUG] 다음 미션 정보: ID={next_mission.mission_id}, 상태={next_mission.status.name}")
                    
                    if battery_level <= self.BATTERY_THRESHOLD:  # 배터리가 임계값 이하면
                        print(f"[🔋 배터리 부족] {truck_id}의 배터리: {battery_level}%")
                        self.set_state(truck_id, TruckState.CHARGING)
                        if self.command_sender:
                            self.command_sender.send(truck_id, "START_CHARGING", {})
                        if self.truck_status_manager:
                            self.truck_status_manager.update_battery(truck_id, battery_level, True)
                        return
                    
                    # 배터리가 충분하면 미션 진행
                    if self.mission_manager.assign_mission_to_truck(next_mission.mission_id, truck_id):
                        self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_LOAD)
                        print(f"[지시] {truck_id} → CHECKPOINT_A로 이동")
                        self.send_run(truck_id)
                        
                        # source 값 확인하고 기본값 설정
                        mission_source = next_mission.source
                        if not mission_source:
                            mission_source = "LOAD_A"  # 기본값 설정
                            print(f"[⚠️ 경고] 미션의 source가 비어있음 - 기본값 '{mission_source}'을 사용합니다")
                        
                        self.command_sender.send(truck_id, "MISSION_ASSIGNED", {
                            "source": mission_source
                        })
                        return
                else:
                    # 미션이 없을 때는 배터리 상태에 따라 처리
                    print(f"[🔋 미션 없음] {truck_id}의 배터리: {battery_level}%")
                    
                    # 먼저 NO_MISSION 메시지를 항상 전송
                    if self.command_sender:
                        if battery_level < self.BATTERY_FULL:
                            self.command_sender.send(truck_id, "NO_MISSION", {"reason": "BATTERY_LOW"})
                        else:
                            self.command_sender.send(truck_id, "NO_MISSION", {"reason": "NO_MISSIONS_AVAILABLE"})
                    
                    # 그 다음 배터리 상태에 따라 충전 명령 보내기
                    if battery_level < self.BATTERY_FULL:  # 배터리가 100%가 아닐 때만 충전
                        print(f"[🔋 충전 필요] {truck_id}의 배터리: {battery_level}% - 충전 상태로 전환")
                        self.set_state(truck_id, TruckState.CHARGING)
                        if self.command_sender:
                            self.command_sender.send(truck_id, "START_CHARGING", {})
                        if self.truck_status_manager:
                            self.truck_status_manager.update_battery(truck_id, battery_level, True)
                    else:
                        print(f"[🔋 충전 불필요] {truck_id}의 배터리: {battery_level}% - 대기 상태 유지")
                        self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)
                return

            # 이미 미션 진행 중일 때 ASSIGN_MISSION 요청이 오면 현재 상태 응답
            elif cmd == "ASSIGN_MISSION":
                current_state = self.get_state(truck_id)
                print(f"[ℹ️ 중복 요청] {truck_id}의 현재 상태: {current_state}")
                
                if current_state == TruckState.MOVE_TO_GATE_FOR_LOAD:
                    # 이미 미션이 할당된 상태면 현재 미션 정보 재전송
                    missions = self.mission_manager.get_assigned_missions_by_truck(truck_id)
                    if missions:
                        mission = missions[0]  # 첫 번째 미션 사용
                        
                        # source 값 확인하고 기본값 설정
                        mission_source = mission.source
                        if not mission_source:
                            mission_source = "LOAD_A"  # 기본값 설정
                            print(f"[⚠️ 경고] 미션의 source가 비어있음 - 기본값 '{mission_source}'을 사용합니다")
                        
                        self.command_sender.send(truck_id, "MISSION_ASSIGNED", {
                            "source": mission_source
                        })
                        return
                elif current_state == TruckState.CHARGING:
                    # 충전 중이면 NO_MISSION 응답
                    self.command_sender.send(truck_id, "NO_MISSION", {"reason": "CHARGING"})
                    return
                elif current_state == TruckState.EMERGENCY_STOP:
                    # 비상 정지 상태면 NO_MISSION 응답
                    self.command_sender.send(truck_id, "NO_MISSION", {"reason": "EMERGENCY"})
                    return
                else:
                    # 기타 상태면 현재 상태 정보만 전송
                    self.command_sender.send(truck_id, "CURRENT_STATE", {
                        "state": str(current_state.name) if hasattr(current_state, 'name') else str(current_state)
                    })
                    return
            
            # -------------------------------- 충전 관련 상태 처리 --------------------------------

            # 충전 중일 때 미션 할당 요청이 오면 NO_MISSION 응답
            elif state == TruckState.CHARGING and cmd == "ASSIGN_MISSION":
                print("[DEBUG] ASSIGN_MISSION: 대기 중인 미션 확인")
                
                # 다음 미션 존재 여부 확인
                waiting_missions = self.mission_manager.get_waiting_missions()
                has_next_mission = len(waiting_missions) > 0
                print(f"[DEBUG] 대기 중인 미션 수: {len(waiting_missions)}")
                
                if has_next_mission:
                    next_mission = waiting_missions[0]
                    print(f"[DEBUG] 다음 미션 정보: ID={next_mission.mission_id}, 상태={next_mission.status.name}")
                    
                if self.command_sender:
                    self.command_sender.send(truck_id, "NO_MISSION", {"reason": "CHARGING"})
                return
            
            # 대기장 도착
            elif state == TruckState.MOVE_TO_STANDBY and cmd == "ARRIVED_AT_STANDBY":
                self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)
                self.handle_trigger(truck_id, "ASSIGN_MISSION", {})
                return
            
            # 충전 완료
            elif state == TruckState.CHARGING and cmd == "FINISH_CHARGING":
                if self.truck_status_manager:
                    truck_status = self.truck_status_manager.get_truck_status(truck_id)
                    if not truck_status["battery"]["level"] >= self.BATTERY_FULL:
                        print(f"[🔋 충전 계속] {truck_id}의 배터리: {truck_status['battery']['level']}%")
                        return
                    
                    self.set_state(truck_id, TruckState.IDLE)
                    if self.command_sender:
                        self.command_sender.send(truck_id, "CHARGING_COMPLETED", {})
                    self.truck_status_manager.update_battery(truck_id, truck_status["battery"]["level"], False)
                    # 충전 완료 후 미션 할당 시도
                    self.handle_trigger(truck_id, "ASSIGN_MISSION", {})
                    return
            
            # WAIT_NEXT_MISSION 상태에서 FINISH_CHARGING 처리 추가
            elif state == TruckState.WAIT_NEXT_MISSION and cmd == "FINISH_CHARGING":
                if self.truck_status_manager:
                    truck_status = self.truck_status_manager.get_truck_status(truck_id)
                    # 충전 상태 해제
                    self.truck_status_manager.update_battery(truck_id, truck_status["battery"]["level"], False)
                    print(f"[🔋 충전 상태 해제] {truck_id}의 배터리: {truck_status['battery']['level']}%")
                    if self.command_sender:
                        self.command_sender.send(truck_id, "CHARGING_COMPLETED", {})
                    return
            
            # -------------------------------- 적재 작업 상태 처리 --------------------------------

            # 게이트 A에 도착
            elif state == TruckState.MOVE_TO_GATE_FOR_LOAD and cmd == "ARRIVED_AT_CHECKPOINT_A":
                self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_LOAD)
                self.send_stop(truck_id)  # 트럭 정지
                gate_id = payload.get("gate_id", "GATE_A")
                self._open_gate_and_log(gate_id, truck_id)
                return
            
            # 게이트 A 열림 확인 (적재)
            elif state == TruckState.WAIT_GATE_OPEN_FOR_LOAD and cmd == "ACK_GATE_OPENED":
                self.set_state(truck_id, TruckState.MOVE_TO_LOAD)
                self.send_run(truck_id)
                return
            
            # CHECKPOINT_B 도착 (GATE_A 닫기)
            elif state == TruckState.MOVE_TO_LOAD and cmd == "ARRIVED_AT_CHECKPOINT_B":
                # self.send_stop(truck_id)  # 트럭 정지
                gate_id = payload.get("gate_id", "GATE_A")
                self._close_gate_and_log(gate_id, truck_id)
                return
            
            # 적재장 도착
            elif state == TruckState.MOVE_TO_LOAD and (cmd == "ARRIVED_AT_LOAD_A" or cmd == "ARRIVED_AT_LOAD_B"):
                self.set_state(truck_id, TruckState.WAIT_LOAD)
                mission = self.mission_manager.find_assigned_mission_by_truck(truck_id)
                if mission and ((cmd == "ARRIVED_AT_LOAD_A" and mission.source == "LOAD_A") or 
                               (cmd == "ARRIVED_AT_LOAD_B" and mission.source == "LOAD_B")):
                    self.send_stop(truck_id)  # 트럭 정지
                return
            
            # 적재 시작
            elif state == TruckState.WAIT_LOAD and cmd == "START_LOADING":
                self.set_state(truck_id, TruckState.LOADING)
                return
            
            # 적재 완료
            elif state == TruckState.LOADING and cmd == "FINISH_LOADING":
                self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_UNLOAD)
                print(f"[지시] {truck_id} → CHECKPOINT_C로 이동")
                self.send_run(truck_id)
                return
                
            # MOVE_TO_LOAD 상태에서 비정상적으로 CHECKPOINT_C 도착 시 처리
            elif state == TruckState.MOVE_TO_LOAD and cmd == "ARRIVED_AT_CHECKPOINT_C":
                print(f"[⚠️ 비정상 경로] {truck_id}가 적재 작업을 건너뛰고 CHECKPOINT_C에 도착함 - 경로 재설정")
                # 이미 하차 게이트에 도착했으므로 적재 작업을 건너뛰고 하차 작업으로 진행
                print(f"[⚠️ 상태 강제 변환] {truck_id}: MOVE_TO_LOAD → MOVE_TO_GATE_FOR_UNLOAD")
                self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_UNLOAD)
                
                # ARRIVED_AT_CHECKPOINT_C 트리거를 다시 발생시켜 게이트 열기 진행
                self.handle_trigger(truck_id, "ARRIVED_AT_CHECKPOINT_C", payload)
                return
                
            # LOADING 상태에서 CHECKPOINT_C에 도착했을 때 처리 추가
            elif state == TruckState.LOADING and cmd == "ARRIVED_AT_CHECKPOINT_C":
                print(f"[ℹ️ 자동 상태 전환] {truck_id}가 로딩 상태에서 CHECKPOINT_C에 도착했습니다. FINISH_LOADING을 자동으로 처리합니다.")
                # 자동으로 FINISH_LOADING 처리
                self.handle_trigger(truck_id, "FINISH_LOADING", {})
                # 상태 업데이트
                self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_UNLOAD)
                # 게이트 열림 처리
                self.handle_trigger(truck_id, "ARRIVED_AT_CHECKPOINT_C", payload)
                return
                
            # WAIT_LOAD 상태에서 CHECKPOINT_C에 도착했을 때 처리 추가
            elif state == TruckState.WAIT_LOAD and cmd == "ARRIVED_AT_CHECKPOINT_C":
                print(f"[ℹ️ 자동 상태 전환] {truck_id}가 로딩 대기 상태에서 CHECKPOINT_C에 도착했습니다. 로딩을 건너뛰고 진행합니다.")
                # 상태 업데이트
                self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_UNLOAD)
                # 게이트 열림 처리
                self.handle_trigger(truck_id, "ARRIVED_AT_CHECKPOINT_C", payload)
                return

            # -------------------------------- 하차 작업 상태 처리 --------------------------------

            # 게이트 B에 도착
            elif state == TruckState.MOVE_TO_GATE_FOR_UNLOAD and cmd == "ARRIVED_AT_CHECKPOINT_C":
                self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_UNLOAD)
                self.send_stop(truck_id)  # 트럭 정지
                gate_id = payload.get("gate_id", "GATE_B")
                self._open_gate_and_log(gate_id, truck_id)
                return
            
            # 게이트 B 열림 확인 (하차)
            elif state == TruckState.WAIT_GATE_OPEN_FOR_UNLOAD and cmd == "ACK_GATE_OPENED":
                self.set_state(truck_id, TruckState.MOVE_TO_UNLOAD)
                self.send_run(truck_id)
                return
            
            # CHECKPOINT_D 도착 (GATE_B 닫기)
            elif state == TruckState.MOVE_TO_UNLOAD and cmd == "ARRIVED_AT_CHECKPOINT_D":
                gate_id = payload.get("gate_id", "GATE_B")
                self._close_gate_and_log(gate_id, truck_id)
                return
            
            # 벨트 도착
            elif state == TruckState.MOVE_TO_UNLOAD and cmd == "ARRIVED_AT_BELT":
                self.set_state(truck_id, TruckState.WAIT_UNLOAD)
                self.send_stop(truck_id)
                return

            # WAIT_GATE_OPEN_FOR_UNLOAD 상태에서 벨트에 도착한 경우 (비정상 경로 보정)
            elif state == TruckState.WAIT_GATE_OPEN_FOR_UNLOAD and cmd == "ARRIVED_AT_BELT":
                self.set_state(truck_id, TruckState.WAIT_UNLOAD)
                self.send_stop(truck_id)
                return

            # WAIT_GATE_OPEN_FOR_UNLOAD 상태에서 하차 작업 시작 (비정상 경로 보정)
            elif state == TruckState.WAIT_GATE_OPEN_FOR_UNLOAD and cmd == "START_UNLOADING":
                self.set_state(truck_id, TruckState.UNLOADING)
                if self.belt_controller:
                    print(f"[FSM] {truck_id} → 벨트에 BELT_RUN 명령 전송")
                    if not self.belt_controller.send_command("BELT", "RUN"):
                        print(f"[⚠️ 경고] {truck_id} → 벨트 작동 거부됨 (컨테이너 가득 참)")
                return

            # WAIT_GATE_OPEN_FOR_UNLOAD 상태에서 하차 완료 (비정상 경로 보정)
            elif state == TruckState.WAIT_GATE_OPEN_FOR_UNLOAD and cmd == "FINISH_UNLOADING":
                self.set_state(truck_id, TruckState.MOVE_TO_STANDBY)
                self.send_run(truck_id)

                mission = self.mission_manager.find_assigned_mission_by_truck(truck_id)
                if mission:
                    # mission.complete() 대신 MissionManager의 complete_mission 사용
                    if self.mission_manager.complete_mission(mission.mission_id):
                        print(f"[✅ 미션 완료] {mission.mission_id} 완료 처리됨")
                    else:
                        print(f"[❌ 미션 완료 실패] {mission.mission_id} - 데이터베이스 업데이트 실패")
                return

            # STANDBY 도착
            elif (state == TruckState.MOVE_TO_STANDBY) and cmd == "ARRIVED_AT_STANDBY":
                self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)
                self.handle_trigger(truck_id, "ASSIGN_MISSION", {})
                return
                
            # MOVE_TO_LOAD 상태에서 STANDBY에 도착한 경우 - 비정상 경로
            elif state == TruckState.MOVE_TO_LOAD and cmd == "ARRIVED_AT_STANDBY":
                print(f"[⚠️ 비정상 경로] {truck_id}가 적재 작업을 완료하지 않고 STANDBY에 도착함")
                self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)
                # 미션 취소 또는 실패로 처리
                mission = self.mission_manager.find_assigned_mission_by_truck(truck_id)
                if mission:
                    print(f"[⚠️ 미션 취소] {mission.mission_id} 강제 취소 처리")
                    self.mission_manager.cancel_mission(mission.mission_id)
                self.handle_trigger(truck_id, "ASSIGN_MISSION", {})
                return
                
            # WAIT_GATE_OPEN_FOR_UNLOAD 상태에서 STANDBY에 도착하는 경우 (비정상 경로 보정)
            elif state == TruckState.WAIT_GATE_OPEN_FOR_UNLOAD and cmd == "ARRIVED_AT_STANDBY":
                print(f"[⚠️ 비정상 경로] {truck_id}가 WAIT_GATE_OPEN_FOR_UNLOAD 상태에서 STANDBY에 도착함")
                self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)
                # 미션 취소 또는 실패로 처리
                mission = self.mission_manager.find_assigned_mission_by_truck(truck_id)
                if mission:
                    print(f"[⚠️ 미션 취소] {mission.mission_id} 강제 취소 처리")
                    self.mission_manager.cancel_mission(mission.mission_id)
                self.handle_trigger(truck_id, "ASSIGN_MISSION", {})
                return

            # 하차 시작
            elif state == TruckState.WAIT_UNLOAD and cmd == "START_UNLOADING":
                self.set_state(truck_id, TruckState.UNLOADING)
                if self.belt_controller:
                    print(f"[FSM] {truck_id} → 벨트에 BELT_RUN 명령 전송")
                    if not self.belt_controller.send_command("BELT", "RUN"):
                        print(f"[⚠️ 경고] {truck_id} → 벨트 작동 거부됨 (컨테이너 가득 참)")
                return

            # 하차 완료
            elif state == TruckState.UNLOADING and cmd == "FINISH_UNLOADING":
                self.set_state(truck_id, TruckState.MOVE_TO_STANDBY)
                self.send_run(truck_id)

                mission = self.mission_manager.find_assigned_mission_by_truck(truck_id)
                if mission:
                    # mission.complete() 대신 MissionManager의 complete_mission 사용
                    if self.mission_manager.complete_mission(mission.mission_id):
                        print(f"[✅ 미션 완료] {mission.mission_id} 완료 처리됨")
                    else:
                        print(f"[❌ 미션 완료 실패] {mission.mission_id} - 데이터베이스 업데이트 실패")
                return

            # -------------------------------- 비상 상황 처리 --------------------------------

            # 비상 상황
            elif cmd == "EMERGENCY_TRIGGERED":
                self.set_state(truck_id, TruckState.EMERGENCY_STOP)
                self.send_stop(truck_id)  # 트럭 정지
                if self.belt_controller:
                    print(f"[FSM] {truck_id} → 벨트에 EMRSTOP 명령 전송")
                    self.belt_controller.send_command("BELT", "EMRSTOP")
                return

            # 비상 상황 해제
            elif state == TruckState.EMERGENCY_STOP and cmd == "RESET":
                self.set_state(truck_id, TruckState.IDLE)
                return
        
            # 상태 초기화
            elif cmd == "RESET":
                print(f"[🔁 RESET] {truck_id} 상태를 IDLE로 초기화")
                
                # 트럭에 할당된 미션이 있으면 대기 상태로 되돌림
                mission = self.mission_manager.find_assigned_mission_by_truck(truck_id)
                if mission:
                    print(f"[⚠️ 미션 취소] {mission.mission_id} 대기 상태로 복귀")
                    self.mission_manager.cancel_mission(mission.mission_id)
                
                self.set_state(truck_id, TruckState.IDLE)
                return

            print(f"[FSM] 상태 전이 없음: 상태={state}, 트리거={cmd}")
        except Exception as e:
            print(f"[FSM] 오류 발생: {e}")