from typing import List, Optional
from .mission import Mission
from .mission_status import MissionStatus
from .mission_db import MissionDB
from datetime import datetime


class MissionManager:
    def __init__(self, db: MissionDB):
        self.db = db
        self.command_sender = None

    # ------------------ 커맨더 설정 ----------------------------

    def set_command_sender(self, command_sender):
        self.command_sender = command_sender

    # ------------------ 미션 생성 ----------------------------

    def create_mission(self, mission_id: str, cargo_type: str, cargo_amount: float,
                       source: str, destination: str) -> Optional[Mission]:
        try:
            mission = Mission(
                mission_id=mission_id,
                cargo_type=cargo_type,
                cargo_amount=cargo_amount,
                source=source,
                destination=destination
            )
            
            mission_data = (
                mission.mission_id,
                mission.cargo_type,
                mission.cargo_amount,
                mission.source,
                mission.destination,
                mission.status.name,
                mission.status.value,
                mission.assigned_truck_id,
                mission.timestamp_created,
                mission.timestamp_assigned,
                mission.timestamp_completed
            )
            
            if self.db.save_mission(mission_data):
                self._notify_trucks_of_waiting_missions()
                print(f"[✅ 미션 생성 완료] {mission.mission_id}")
                return mission
            
            print(f"[❌ 미션 생성 실패] {mission.mission_id}")
            return None
        
        except Exception as err:
            print(f"[❌ 미션 생성 실패] {err}")
            return None

    # ------------------ 미션 할당 ----------------------------

    def assign_mission_to_truck(self, mission_id: str, truck_id: str) -> bool:
        mission_data = self.db.find_mission_by_id(mission_id)
        
        if not mission_data:
            print(f"[❌ 미션 할당 실패] 미션 {mission_id}을 찾을 수 없음")
            return False
        
        try:
            mission = Mission.from_row(mission_data)
            mission.assign_to_truck(truck_id)
            
            mission_data = (
                mission.mission_id,
                mission.cargo_type,
                mission.cargo_amount,
                mission.source,
                mission.destination,
                mission.status.name,
                mission.status.value,
                mission.assigned_truck_id,
                mission.timestamp_created,
                mission.timestamp_assigned,
                mission.timestamp_completed
            )
            
            if self.db.save_mission(mission_data):
                print(f"[✅ 미션 할당 완료] {mission_id} → {truck_id}")
                return True
            
            print(f"[❌ 미션 할당 실패] {mission_id} → {truck_id}")
            return False
        
        except Exception as err:
            print(f"[❌ 미션 할당 실패] {err}")
            return False

    # ------------------ 미션 완료 ----------------------------

    def complete_mission(self, mission_id: str) -> bool:
        mission_data = self.db.find_mission_by_id(mission_id)
        
        if not mission_data:
            print(f"[❌ 미션 완료 실패] 미션 {mission_id}을 찾을 수 없음")
            return False
        
        try:
            print(f"[디버그] 미션 {mission_id}의 현재 상태: {mission_data['status_code']}")
            
            mission = Mission.from_row(mission_data)
            mission.complete()
            
            print(f"[디버그] 미션 {mission_id}의 새 상태: {mission.status.name}")
            print(f"[디버그] 완료 시간: {mission.timestamp_completed}")
            
            mission_data = (
                mission.mission_id,
                mission.cargo_type,
                mission.cargo_amount,
                mission.source,
                mission.destination,
                mission.status.name,
                mission.status.value,
                mission.assigned_truck_id,
                mission.timestamp_created,
                mission.timestamp_assigned,
                mission.timestamp_completed
            )
            
            # 직접 DB에 완료 상태 업데이트 (save_mission 메서드 대신)
            status_code = mission.status.name
            status_label = mission.status.value
            timestamp_completed = mission.timestamp_completed
            
            # 두 가지 방법으로 DB 업데이트 시도
            save_result = self.db.save_mission(mission_data)
            update_result = self.db.update_mission_completion(
                mission_id=mission.mission_id,
                status_code=status_code,
                status_label=status_label,
                timestamp_completed=timestamp_completed
            )
            
            if save_result and update_result:
                print(f"[✅ 미션 완료 처리] {mission_id} (DB 저장 및 업데이트 성공)")
                return True
            elif save_result:
                print(f"[⚠️ 미션 완료 처리] {mission_id} (DB 저장만 성공, 업데이트 실패)")
                return True
            elif update_result:
                print(f"[⚠️ 미션 완료 처리] {mission_id} (DB 업데이트만 성공, 저장 실패)")
                return True
            else:
                print(f"[❌ 미션 완료 실패] {mission_id} (DB 저장 및 업데이트 실패)")
                return False
            
        except Exception as err:
            print(f"[❌ 미션 완료 실패] {err}")
            import traceback
            traceback.print_exc()
            return False

    # ------------------ 미션 취소 ----------------------------

    def cancel_mission(self, mission_id: str) -> bool:
        mission_data = self.db.find_mission_by_id(mission_id)
        
        if not mission_data:
            print(f"[❌ 미션 취소 실패] 미션 {mission_id}을 찾을 수 없음")
            return False
        
        try:
            mission = Mission.from_row(mission_data)
            mission.cancel()
            
            mission_data = (
                mission.mission_id,
                mission.cargo_type,
                mission.cargo_amount,
                mission.source,
                mission.destination,
                mission.status.name,
                mission.status.value,
                mission.assigned_truck_id,
                mission.timestamp_created,
                mission.timestamp_assigned,
                mission.timestamp_completed
            )
            
            if self.db.save_mission(mission_data):
                self._notify_trucks_of_waiting_missions()
                print(f"[✅ 미션 취소 완료] {mission_id}")
                return True
            
            print(f"[❌ 미션 취소 실패] {mission_id}")
            return False
        
        except Exception as err:
            print(f"[❌ 미션 취소 실패] {err}")
            return False

    # ------------------ 미션 조회 ----------------------------

    def find_mission_by_id(self, mission_id: str) -> Optional[Mission]:
        mission_data = self.db.find_mission_by_id(mission_id)
        return Mission.from_row(mission_data) if mission_data else None

    def get_assigned_missions_by_truck(self, truck_id: str) -> List[Mission]:
        mission_rows = self.db.get_missions_by_truck(truck_id)
        return [Mission.from_row(row) for row in mission_rows]

    def find_assigned_mission_by_truck(self, truck_id: str) -> Optional[Mission]:
        missions = self.get_assigned_missions_by_truck(truck_id)
        return missions[0] if missions else None

    def get_waiting_missions(self) -> List[Mission]:
        mission_rows = self.db.get_waiting_missions()
        return [Mission.from_row(row) for row in mission_rows]

    def get_assigned_and_waiting_missions(self) -> List[Mission]:
        mission_rows = self.db.get_assigned_and_waiting_missions()
        return [Mission.from_row(row) for row in mission_rows]

    # ------------------ 미션 알림 ----------------------------

    def _notify_trucks_of_waiting_missions(self) -> None:
        if not self.command_sender:
            return
        
        waiting_missions = self.get_waiting_missions()
        if waiting_missions:
            print(f"[📢 미션 알림] 대기 중인 미션 {len(waiting_missions)}개가 있습니다.")
            for truck_id in self.command_sender.truck_sockets.keys():
                self.command_sender.send(truck_id, "MISSIONS_AVAILABLE", {
                    "count": len(waiting_missions)
                })
