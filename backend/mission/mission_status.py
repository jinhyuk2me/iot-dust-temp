# backend/mission/mission_status.py

from enum import Enum

class MissionStatus(Enum):
    WAITING = "대기중"
    ASSIGNED = "트럭 배정됨"
    COMPLETED = "완료됨"
    CANCELED = "취소됨"
    ERROR = "오류"