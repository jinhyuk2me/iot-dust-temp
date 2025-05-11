import mysql.connector
from datetime import datetime
from typing import Optional, List, Dict

class TruckStatusDB:
    def __init__(self, host="localhost", user="root", password="jinhyuk2dacibul", database="dust"):
        self.connection_params = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.init_db()

    def get_connection(self):
        return mysql.connector.connect(**self.connection_params)

    def init_db(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 배터리 상태 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS battery_status (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    truck_id VARCHAR(50),
                    battery_level FLOAT,
                    truck_status VARCHAR(50),
                    event_type VARCHAR(50),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
            """)

            # 위치 상태 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_status (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    truck_id VARCHAR(50),
                    location VARCHAR(50),
                    status VARCHAR(50),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
            """)
            
            # TRUCK_01의 초기 상태 데이터 생성
            cursor.execute("""
                INSERT IGNORE INTO battery_status (truck_id, battery_level, truck_status, event_type)
                VALUES ('TRUCK_01', 100.0, 'NORMAL', 'CHARGING_END')
            """)
            
            cursor.execute("""
                INSERT IGNORE INTO position_status (truck_id, location, status)
                VALUES ('TRUCK_01', 'STANDBY', 'IDLE')
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            print("[DEBUG] 트럭 상태 데이터베이스 초기화 완료")
        
        except mysql.connector.Error as err:
            print(f"[ERROR] DB 초기화 실패: {err}")

    def reset_all_statuses(self):
        """모든 트럭 상태 기록 초기화"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM position_status")
            cursor.execute("DELETE FROM battery_status")
            conn.commit()
            cursor.close()
            conn.close()
            print("[✅ 트럭 상태 초기화 완료] 모든 트럭 상태 기록이 삭제되었습니다")
        except mysql.connector.Error as err:
            print(f"[ERROR] 상태 초기화 실패: {err}")

    def log_battery_status(self, truck_id: str, battery_level: float, truck_status: str, event_type: str):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO battery_status (truck_id, battery_level, truck_status, event_type)
                VALUES (%s, %s, %s, %s)
            """, (truck_id, battery_level, truck_status, event_type))
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"[ERROR] 배터리 상태 로깅 실패: {err}")

    def log_position_status(self, truck_id: str, position: str, run_state: str = None):
        """
        트럭의 위치 상태를 로깅합니다.
        
        Args:
            truck_id (str): 트럭 ID
            current (str): 트럭이 마지막으로 인식한 포인트
            run_state (str): 트럭의 주행 상태
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO position_status (truck_id, location, status)
                VALUES (%s, %s, %s)
            """, (truck_id, position, run_state if run_state else "IDLE"))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[DEBUG] 위치 상태 로깅 완료: {truck_id} - position={position}, run_state={run_state}")
        except Exception as e:
            print(f"[ERROR] 위치 상태 로깅 실패: {str(e)}")

    def get_latest_battery_status(self, truck_id: str) -> Optional[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT battery_level, truck_status, event_type, timestamp
                FROM battery_status
                WHERE truck_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (truck_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row if row else None
        except mysql.connector.Error as err:
            print(f"[ERROR] 배터리 상태 조회 실패: {err}")
            return None

    def get_latest_position_status(self, truck_id: str) -> Optional[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT location, status, timestamp
                FROM position_status
                WHERE truck_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (truck_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row if row else None
        except mysql.connector.Error as err:
            print(f"[ERROR] 위치 상태 조회 실패: {err}")
            return None

    def get_battery_history(self, truck_id: str, limit: int = 100) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT battery_level, truck_status, event_type, timestamp
                FROM battery_status
                WHERE truck_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (truck_id, limit))
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
        except mysql.connector.Error as err:
            print(f"[ERROR] 배터리 히스토리 조회 실패: {err}")
            return []

    def get_position_history(self, truck_id: str, limit: int = 100) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT location, status, timestamp
                FROM position_status
                WHERE truck_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (truck_id, limit))
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
        except mysql.connector.Error as err:
            print(f"[ERROR] 위치 히스토리 조회 실패: {err}")
            return []

    def close(self):
        print("[DEBUG] TruckStatusDB 리소스 정리 완료")
