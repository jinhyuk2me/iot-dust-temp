from backend.truck_status.truck_status_manager import TruckStatusManager
from backend.truck_status.truck_status_db import TruckStatusDB
from backend.mission.mission_manager import MissionManager
from backend.mission.mission_db import MissionDB
from backend.facility_status.facility_status_manager import FacilityStatusManager
from backend.facility_status.facility_status_db import FacilityStatusDB

# 전역 상태 관리 인스턴스
truck_status_manager = None
mission_manager = None
facility_status_manager = None

# ------------------ 초기화 함수 ----------------------------

def get_truck_status_manager():
    """TruckStatusManager 초기화"""
    global truck_status_manager
    if truck_status_manager is None:
        print("[DEBUG] TruckStatusManager 초기화")
        status_db = TruckStatusDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        truck_status_manager = TruckStatusManager(status_db)
        print("[DEBUG] TruckStatusManager 초기화 완료")
    return truck_status_manager

def get_mission_manager():
    """MissionManager 초기화"""
    global mission_manager
    if mission_manager is None:
        print("[DEBUG] MissionManager 초기화")
        mission_db = MissionDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        mission_manager = MissionManager(mission_db)
        print("[DEBUG] MissionManager 초기화 완료")
    return mission_manager

def get_facility_status_manager():
    """FacilityStatusManager 초기화"""
    global facility_status_manager
    if facility_status_manager is None:
        print("[DEBUG] FacilityStatusManager 초기화")
        facility_db = FacilityStatusDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        facility_status_manager = FacilityStatusManager(facility_db)
        print("[DEBUG] FacilityStatusManager 초기화 완료")
    return facility_status_manager

# ------------------ 종료 함수 ----------------------------

def cleanup_managers():
    """애플리케이션 종료 시 리소스 정리"""
    global truck_status_manager, mission_manager, facility_status_manager
    if truck_status_manager is not None:
        print("[DEBUG] TruckStatusManager 종료")
        truck_status_manager.close()
        truck_status_manager = None

    if mission_manager is not None:
        print("[DEBUG] MissionManager 종료")
        mission_manager.db.close()
        mission_manager = None
        
    if facility_status_manager is not None:
        print("[DEBUG] FacilityStatusManager 종료")
        facility_status_manager.close()
        facility_status_manager = None 