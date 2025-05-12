from datetime import datetime
from typing import Optional, Dict, List
from .mission_status import MissionStatus


class Mission:
    def __init__(self, mission_id: str, cargo_type: str, cargo_amount: float,
                 source: str, destination: str, assigned_truck_id: Optional[str] = None,
                 status: MissionStatus = MissionStatus.WAITING,
                 timestamp_created: Optional[datetime] = None,
                 timestamp_assigned: Optional[datetime] = None,
                 timestamp_completed: Optional[datetime] = None):
        
        self.mission_id = mission_id
        self.cargo_type = cargo_type
        self.cargo_amount = cargo_amount
        self.source = source
        self.destination = destination
        self.assigned_truck_id = assigned_truck_id
        self.status = status
        self.timestamp_created = timestamp_created or datetime.now()
        self.timestamp_assigned = timestamp_assigned
        self.timestamp_completed = timestamp_completed

    # ------------------ 미션 할당 ----------------------------

    def assign_to_truck(self, truck_id: str) -> None:
        """트럭에 미션 할당"""
        if self.status != MissionStatus.WAITING:
            raise ValueError("대기 중인 미션만 할당 가능합니다")
        
        self.assigned_truck_id = truck_id
        self.status = MissionStatus.ASSIGNED
        self.timestamp_assigned = datetime.now()

    # ------------------ 미션 완료 ----------------------------

    def complete(self) -> None:
        if self.status != MissionStatus.ASSIGNED:
            raise ValueError("할당된 미션만 완료할 수 있습니다")
        
        self.status = MissionStatus.COMPLETED
        self.timestamp_completed = datetime.now()

    # ------------------ 미션 취소 ----------------------------

    def cancel(self) -> None:
        if self.status == MissionStatus.COMPLETED:
            raise ValueError("완료된 미션은 취소할 수 없습니다")
        
        self.status = MissionStatus.CANCELED

    # ------------------ 상태 전이 ----------------------------

    def update_status(self, new_status) -> None:
        # 문자열로 상태가 전달된 경우 MissionStatus로 변환
        if isinstance(new_status, str):
            try:
                new_status = MissionStatus[new_status]
            except KeyError:
                raise ValueError(f"유효하지 않은 상태: {new_status}")
        
        if not self._is_valid_status_transition(new_status):
            print(f"[⚠️ 잘못된 상태 전이] {self.status} → {new_status}")
            raise ValueError(f"잘못된 상태 전이: {self.status} → {new_status}")
        
        self.status = new_status
        
        if new_status == MissionStatus.COMPLETED:
            self.timestamp_completed = datetime.now()

    def _is_valid_status_transition(self, new_status: MissionStatus) -> bool:
        valid_transitions = {
            MissionStatus.WAITING: [MissionStatus.ASSIGNED, MissionStatus.CANCELED],
            MissionStatus.ASSIGNED: [MissionStatus.COMPLETED, MissionStatus.CANCELED, MissionStatus.ERROR],
            MissionStatus.ERROR: [MissionStatus.CANCELED],
            MissionStatus.CANCELED: [],
            MissionStatus.COMPLETED: []
        }
        return new_status in valid_transitions.get(self.status, [])

    # ------------------ 데이터 직렬화 ----------------------------

    def to_dict(self) -> Dict:
        return {
            "mission_id": self.mission_id,
            "cargo_type": self.cargo_type,
            "cargo_amount": self.cargo_amount,
            "source": self.source,
            "destination": self.destination,
            "status": {
                "code": self.status.name,
                "label": self.status.value
            },
            "assigned_truck_id": self.assigned_truck_id,
            "timestamp_created": self.timestamp_created.isoformat() if self.timestamp_created else None,
            "timestamp_assigned": self.timestamp_assigned.isoformat() if self.timestamp_assigned else None,
            "timestamp_completed": self.timestamp_completed.isoformat() if self.timestamp_completed else None,
        }

    @staticmethod
    def from_row(row: Dict) -> 'Mission':
        return Mission(
            mission_id=row["mission_id"],
            cargo_type=row["cargo_type"],
            cargo_amount=row["cargo_amount"],
            source=row["source"],
            destination=row["destination"],
            assigned_truck_id=row["assigned_truck_id"],
            status=MissionStatus[row["status_code"]],
            timestamp_created=row["timestamp_created"],
            timestamp_assigned=row["timestamp_assigned"],
            timestamp_completed=row["timestamp_completed"]
        )
