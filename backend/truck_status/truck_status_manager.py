from typing import Dict, Optional
from datetime import datetime
from .truck_status_db import TruckStatusDB

class TruckStatusManager:
    def __init__(self, db: TruckStatusDB):
        self.truck_status_db = db
        self.truck_status = {}
        self.fsm_states = {}  # 트럭의 FSM 상태를 별도로 저장하는 딕셔너리
    
    # -------------------------------- 트럭 상태 초기화 --------------------------------
    def reset_all_trucks(self):
        """모든 트럭 상태를 초기화"""
        self.truck_status = {}  # 메모리 상의 상태 초기화
        self.fsm_states = {}    # FSM 상태 초기화
        # DB 상태도 초기화
        self.truck_status_db.reset_all_statuses()
        print("[✅ 메모리 상태 초기화 완료] 모든 트럭 상태가 초기화되었습니다")
    
    # -------------------------------- 트럭 상태 조회 --------------------------------
    def get_truck_status(self, truck_id: str) -> dict:
        """트럭 상태 조회 - DB에서 최신 상태를 가져와 메모리 업데이트"""
        # DB에서 최신 상태 조회
        battery_data = self.truck_status_db.get_latest_battery_status(truck_id)
        position_data = self.truck_status_db.get_latest_position_status(truck_id)

        # 배터리 초기화
        battery_status = {
            "level": 100.0,
            "is_charging": False
        }
        if battery_data:
            battery_status = {
                "level": battery_data["battery_level"],
                "is_charging": battery_data["event_type"] == "CHARGING_START"
            }

        # 위치 초기화
        position_status = {
            "location": "UNKNOWN",
            "status": "IDLE"
        }
        if position_data:
            position_status = {
                "location": position_data["location"],
                "status": position_data["status"]
            }

        # 메모리 상태 업데이트
        self.truck_status[truck_id] = {
            "battery": battery_status,
            "position": position_status
        }
        
        # FSM 상태 조회
        fsm_state = self.get_fsm_state(truck_id)
        
        # 응답에 FSM 상태 포함
        result = self.truck_status[truck_id].copy()
        result["fsm_state"] = fsm_state

        return result
    
    # -------------------------------- 배터리 상태 업데이트 --------------------------------

    def update_battery(self, truck_id: str, level: float, is_charging: bool):
        """배터리 상태 업데이트"""
        # DB에 로깅
        self.truck_status_db.log_battery_status(
            truck_id=truck_id,
            battery_level=level,
            truck_status="CHARGING" if is_charging else "NORMAL",
            event_type="CHARGING_START" if is_charging else "CHARGING_END"
        )
        
        # 메모리 상태 업데이트
        if truck_id not in self.truck_status:
            self.truck_status[truck_id] = {
                "battery": {"level": level, "is_charging": is_charging},
                "position": {"location": "UNKNOWN", "status": "IDLE"}
            }
        else:
            self.truck_status[truck_id]["battery"]["level"] = level
            self.truck_status[truck_id]["battery"]["is_charging"] = is_charging
        
        # 상태 변화 로깅
        print(f"[🔋 배터리 상태] {truck_id}: {level}% (충전상태: {is_charging})")
    
    # -------------------------------- 위치 상태 업데이트 --------------------------------

    def update_position(self, truck_id: str, position: str, run_state: str = None):
        """
        트럭의 위치 정보를 업데이트합니다. FSM 상태는 변경하지 않습니다.
        
        Args:
            truck_id (str): 트럭 ID
            position (str): 현재 위치
            run_state (str): 트럭의 실행 상태
        """
        try:
            # run_state가 TruckState 객체인 경우에만 문자열로 변환
            if hasattr(run_state, 'name'):
                run_state_str = run_state.name
            elif hasattr(run_state, 'value'):
                run_state_str = run_state.value
            else:
                # 이미 문자열이거나 다른 타입인 경우 그대로 사용
                run_state_str = run_state if run_state else "IDLE"
            
            # 위치 정보 로깅
            self.truck_status_db.log_position_status(truck_id, position, run_state_str)
            
            # 메모리 상태 업데이트 (위치 및 상태 정보만)
            if truck_id not in self.truck_status:
                self.truck_status[truck_id] = {
                    "battery": {"level": 100, "is_charging": False},
                    "position": {"location": "UNKNOWN", "status": "IDLE"}
                }
            
            # 위치 정보만 업데이트 (FSM 상태는 건드리지 않음)
            self.truck_status[truck_id]["position"] = {
                "location": position,
                "status": run_state_str
            }
            
            print(f"[DEBUG] 위치 업데이트 완료: {truck_id} - position={position}, run_state={run_state_str}")
            
        except Exception as e:
            print(f"[ERROR] 위치 업데이트 실패: {str(e)}")

    # -------------------------------- 조회 --------------------------------
    
    def get_all_trucks(self) -> Dict[str, dict]:
        """모든 트럭의 상태 조회 - DB에서 최신 상태를 가져와 메모리 업데이트"""
        try:
            # 현재는 TRUCK_01만 사용
            truck_id = "TRUCK_01"
            
            # DB에서 최신 상태 조회
            battery_data = self.truck_status_db.get_latest_battery_status(truck_id)
            position_data = self.truck_status_db.get_latest_position_status(truck_id)

            # 배터리 초기화
            battery_status = {
                "level": 100.0,
                "is_charging": False
            }
            if battery_data:
                battery_status = {
                    "level": battery_data["battery_level"],
                    "is_charging": battery_data["event_type"] == "CHARGING_START"
                }

            # 위치 초기화
            position_status = {
                "location": "STANDBY",  # 기본값을 STANDBY로 변경
                "status": "IDLE"
            }
            if position_data:
                position_status = {
                    "location": position_data["location"],
                    "status": position_data["status"]
                }

            # 메모리 상태 업데이트
            self.truck_status[truck_id] = {
                "battery": battery_status,
                "position": position_status
            }
            
            # FSM 상태도 포함하여 결과 생성
            result = {}
            for t_id, status in self.truck_status.items():
                result[t_id] = status.copy()
                result[t_id]["fsm_state"] = self.get_fsm_state(t_id)

            # 항상 최소한 하나의 트럭 상태를 반환
            return result
        except Exception as e:
            print(f"[ERROR] 트럭 상태 조회 중 오류 발생: {e}")
            # 오류 발생 시 기본 상태 반환
            return {
                "TRUCK_01": {
                    "battery": {"level": 100.0, "is_charging": False},
                    "position": {"location": "STANDBY", "status": "IDLE"},
                    "fsm_state": "IDLE"
                }
            }
    
    def get_battery_history(self, truck_id: str, limit: int = 100):
        """배터리 히스토리 조회"""
        return self.truck_status_db.get_battery_history(truck_id, limit)
    
    def get_position_history(self, truck_id: str, limit: int = 100):
        """위치 히스토리 조회"""
        return self.truck_status_db.get_position_history(truck_id, limit)
    
    # -------------------------------- FSM 상태 관리 --------------------------------

    def get_fsm_state(self, truck_id: str) -> str:
        """트럭의 FSM 상태 조회"""
        return self.fsm_states.get(truck_id, "IDLE")

    def set_fsm_state(self, truck_id: str, fsm_state: str):
        """트럭의 FSM 상태 설정"""
        self.fsm_states[truck_id] = fsm_state
        print(f"[FSM 상태 설정] {truck_id}: {fsm_state}")
    
    def close(self):
        """리소스 정리"""
        self.truck_status_db.close()
        print("[DEBUG] TruckStatusManager 리소스 정리 완료")
