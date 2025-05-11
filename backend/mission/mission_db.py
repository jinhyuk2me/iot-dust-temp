import mysql.connector
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime


class MissionDB:
    def __init__(self, host="localhost", user="root", password="jinhyuk2dacibul", database="dust"):
        self.connection_params = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.init_db()
    
    def get_connection(self):
        """MySQL 연결 반환"""
        return mysql.connector.connect(**self.connection_params)

    def init_db(self):
        """미션 테이블 초기화"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 미션 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id VARCHAR(36) PRIMARY KEY,
                    cargo_type VARCHAR(100) NOT NULL,
                    cargo_amount FLOAT NOT NULL,
                    source VARCHAR(100) NOT NULL,
                    destination VARCHAR(100) NOT NULL,
                    status_code VARCHAR(50) NOT NULL,
                    status_label VARCHAR(100) NOT NULL,
                    assigned_truck_id VARCHAR(20),
                    timestamp_created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    timestamp_assigned DATETIME,
                    timestamp_completed DATETIME,
                    INDEX idx_status (status_code),
                    INDEX idx_truck (assigned_truck_id)
                ) ENGINE=InnoDB;
            """)
            conn.commit()
            cursor.close()
            conn.close()
            print("[✅ DB 초기화 완료] 미션 테이블 생성 완료")
        
        except mysql.connector.Error as err:
            print(f"[❌ DB 초기화 실패] {err}")

    # ------------------ 쿼리 실행 ----------------------------

    def execute(self, query: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """쿼리 실행 및 결과 반환"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 디버깅 로그
            param_str = str(params) if params else "없음"
            print(f"[DB 쿼리 실행] {query[:100]}{'...' if len(query) > 100 else ''}")
            print(f"[DB 파라미터] {param_str[:100]}{'...' if len(param_str) > 100 else ''}")
            
            cursor.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                result = cursor.fetchall()
                print(f"[DB 조회 결과] {len(result)}개 행 반환")
            else:
                conn.commit()
                result = []
                print(f"[DB 변경 완료] 영향받은 행 수: {cursor.rowcount}")
            return result
        except mysql.connector.Error as err:
            print(f"[❌ DB 쿼리 실행 실패] 오류 코드: {err.errno}, 메시지: {err.msg}")
            print(f"[❌ 실패한 쿼리] {query}")
            print(f"[❌ 실패한 파라미터] {params}")
            if conn and conn.is_connected():
                conn.rollback()
            return []
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    def execute_transaction(self, queries: List[Dict[str, Any]]) -> bool:
        """트랜잭션 실행"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            for query_data in queries:
                cursor.execute(query_data['query'], query_data.get('params', None))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except mysql.connector.Error as err:
            print(f"[❌ 트랜잭션 실패] {err}")
            return False

    # ------------------ 미션 저장 ----------------------------

    def save_mission(self, mission_data: Tuple) -> bool:
        """미션 저장"""
        try:
            # 로그 출력을 위한 미션 데이터 파싱
            mission_id = mission_data[0] if len(mission_data) > 0 else "알 수 없음"
            status_code = mission_data[5] if len(mission_data) > 5 else "알 수 없음"
            timestamp_completed = mission_data[10] if len(mission_data) > 10 else None
            
            print(f"[미션 저장 시작] ID: {mission_id}, 상태: {status_code}, 완료 시간: {timestamp_completed}")
            
            query = """
                INSERT INTO missions (
                    mission_id, cargo_type, cargo_amount, source, destination,
                    status_code, status_label, assigned_truck_id,
                    timestamp_created, timestamp_assigned, timestamp_completed
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    status_code = VALUES(status_code),
                    status_label = VALUES(status_label),
                    assigned_truck_id = VALUES(assigned_truck_id),
                    timestamp_assigned = VALUES(timestamp_assigned),
                    timestamp_completed = VALUES(timestamp_completed)
            """
            result = self.execute(query, mission_data)
            print(f"[미션 저장 완료] ID: {mission_id}, 상태: {status_code}")
            return True
        except Exception as err:
            print(f"[❌ 미션 저장 실패] {err}")
            if mission_data and len(mission_data) > 0:
                print(f"[❌ 저장 실패한 미션 ID] {mission_data[0]}")
            import traceback
            traceback.print_exc()
            return False

    # ------------------ 미션 조회 ----------------------------

    def get_waiting_missions(self) -> List[Dict[str, Any]]:
        """대기 중인 미션 조회"""
        query = """
            SELECT * FROM missions
            WHERE status_code = 'WAITING'
            ORDER BY timestamp_created ASC
        """
        return self.execute(query)

    def get_assigned_and_waiting_missions(self) -> List[Dict[str, Any]]:
        """할당된 미션과 대기 미션, 완료된 미션 조회"""
        query = """
            SELECT * FROM missions
            WHERE status_code IN ('WAITING', 'ASSIGNED', 'COMPLETED')
            ORDER BY timestamp_created ASC
        """
        return self.execute(query)

    def find_mission_by_id(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """미션 ID로 미션 조회"""
        query = "SELECT * FROM missions WHERE mission_id = %s"
        results = self.execute(query, (mission_id,))
        return results[0] if results else None

    def get_missions_by_truck(self, truck_id: str) -> List[Dict[str, Any]]:
        """트럭 ID로 할당된 미션 목록 조회"""
        query = """
            SELECT * FROM missions
            WHERE assigned_truck_id = %s
            AND status_code = 'ASSIGNED'
            ORDER BY timestamp_assigned ASC
        """
        return self.execute(query, (truck_id,))

    # ------------------ 미션 상태 업데이트 ----------------------------

    def update_mission_completion(self, mission_id: str, status_code: str, status_label: str, timestamp_completed: datetime = None) -> bool:
        """미션 완료 처리"""
        try:
            query = """
                UPDATE missions
                SET status_code = %s, 
                    status_label = %s,
                    timestamp_completed = %s
                WHERE mission_id = %s
            """
            params = (status_code, status_label, timestamp_completed, mission_id)
            print(f"[미션 업데이트] 미션 ID: {mission_id}, 상태: {status_code}, 완료 시간: {timestamp_completed}")
            result = self.execute(query, params)
            print(f"[미션 업데이트 결과] {result}")
            return True
        except Exception as err:
            print(f"[❌ 미션 완료 처리 실패] {err}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_mission_assignment(self, mission_id: str, truck_id: str) -> bool:
        """미션 할당 정보 업데이트"""
        try:
            query = """
                UPDATE missions
                SET assigned_truck_id = %s,
                    status_code = 'ASSIGNED',
                    status_label = '트럭 배정됨',
                    timestamp_assigned = %s
                WHERE mission_id = %s
            """
            self.execute(query, (truck_id, datetime.now(), mission_id))
            return True
        except Exception as err:
            print(f"[❌ 미션 할당 실패] {err}")
            return False

    def close(self):
        print("[✅ MissionDB 리소스 정리 완료]")
