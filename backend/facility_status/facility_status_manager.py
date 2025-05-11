from typing import Dict, Optional, List
from datetime import datetime
from .facility_status_db import FacilityStatusDB

class FacilityStatusManager:
    def __init__(self, db: FacilityStatusDB):
        self.facility_status_db = db
        self.gate_status = {}
        self.belt_status = {}
    
    # -------------------------------- 시설 상태 초기화 --------------------------------
    
    def reset_all_facilities(self):
        """모든 시설 상태를 초기화"""
        self.gate_status = {}  # 메모리 상의 게이트 상태 초기화
        self.belt_status = {}  # 메모리 상의 벨트 상태 초기화
        
        # DB 상태도 초기화
        self.facility_status_db.reset_all_statuses()
        print("[✅ 메모리 상태 초기화 완료] 모든 시설 상태가 초기화되었습니다")
        
        # 기본 상태 추가
        self.update_gate_status("GATE_A", "CLOSED", "IDLE")
        self.update_gate_status("GATE_B", "CLOSED", "IDLE")
        self.update_belt_status("BELT", "STOPPED", "IDLE", "EMPTY")
    
    # -------------------------------- 게이트 상태 관리 --------------------------------
    
    def update_gate_status(self, gate_id: str, state: str, operation: str):
        """게이트 상태 업데이트"""
        # DB에 로깅
        self.facility_status_db.log_gate_status(
            gate_id=gate_id,
            state=state,
            operation=operation
        )
        
        # 메모리 상태 업데이트
        self.gate_status[gate_id] = {
            "state": state,
            "operation": operation,
            "timestamp": datetime.now()
        }
        
        # 상태 변화 로깅
        print(f"[🚪 게이트 상태] {gate_id}: {state} (동작: {operation})")
    
    def get_gate_status(self, gate_id: str) -> dict:
        """게이트 상태 조회 - DB에서 최신 상태를 가져와 메모리 업데이트"""
        # DB에서 최신 상태 조회
        gate_data = self.facility_status_db.get_latest_gate_status(gate_id)
        
        # 초기 상태
        gate_status = {
            "state": "CLOSED",
            "operation": "IDLE",
            "timestamp": datetime.now()
        }
        
        if gate_data:
            gate_status = {
                "state": gate_data["state"],
                "operation": gate_data["operation"],
                "timestamp": gate_data["timestamp"]
            }
        
        # 메모리 상태 업데이트
        self.gate_status[gate_id] = gate_status
        
        return gate_status
    
    # -------------------------------- 벨트 상태 관리 --------------------------------
    
    def update_belt_status(self, belt_id: str, state: str, operation: str, container_state: str):
        """벨트 상태 업데이트"""
        # DB에 로깅
        self.facility_status_db.log_belt_status(
            belt_id=belt_id,
            state=state,
            operation=operation,
            container_state=container_state
        )
        
        # 메모리 상태 업데이트
        self.belt_status[belt_id] = {
            "state": state,
            "operation": operation,
            "container_state": container_state,
            "timestamp": datetime.now()
        }
        
        # 상태 변화 로깅
        print(f"[🧭 벨트 상태] {belt_id}: {state} (동작: {operation}, 컨테이너: {container_state})")
    
    def get_belt_status(self, belt_id: str) -> dict:
        """벨트 상태 조회 - DB에서 최신 상태를 가져와 메모리 업데이트"""
        # DB에서 최신 상태 조회
        belt_data = self.facility_status_db.get_latest_belt_status(belt_id)
        
        # 초기 상태
        belt_status = {
            "state": "STOPPED",
            "operation": "IDLE",
            "container_state": "EMPTY",
            "timestamp": datetime.now()
        }
        
        if belt_data:
            belt_status = {
                "state": belt_data["state"],
                "operation": belt_data["operation"],
                "container_state": belt_data["container_state"],
                "timestamp": belt_data["timestamp"]
            }
        
        # 메모리 상태 업데이트
        self.belt_status[belt_id] = belt_status
        
        return belt_status
    
    # -------------------------------- 모든 시설 상태 조회 --------------------------------
    
    def get_all_facilities(self) -> Dict[str, dict]:
        """모든 시설의 상태 조회"""
        result = {}
        
        # 게이트 상태 조회
        gate_ids = ["GATE_A", "GATE_B"]
        for gate_id in gate_ids:
            result[gate_id] = self.get_gate_status(gate_id)
        
        # 벨트 상태 조회
        belt_ids = ["BELT"]
        for belt_id in belt_ids:
            result[belt_id] = self.get_belt_status(belt_id)
        
        return result
    
    # -------------------------------- 히스토리 조회 --------------------------------
    
    def get_gate_history(self, gate_id: str, limit: int = 100) -> List[Dict]:
        """게이트 히스토리 조회"""
        return self.facility_status_db.get_gate_history(gate_id, limit)
    
    def get_belt_history(self, belt_id: str, limit: int = 100) -> List[Dict]:
        """벨트 히스토리 조회"""
        return self.facility_status_db.get_belt_history(belt_id, limit)
    
    def close(self):
        """리소스 정리"""
        self.facility_status_db.close()
        print("[DEBUG] FacilityStatusManager 리소스 정리 완료")
