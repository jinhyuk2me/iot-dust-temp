import mysql.connector
from datetime import datetime
from typing import Optional, List, Dict

class FacilityStatusDB:
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

            # 게이트 상태 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gate_status (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    gate_id VARCHAR(50),
                    state VARCHAR(50),                 
                    operation VARCHAR(50),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
            """)

            # 벨트 상태 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS belt_status (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    belt_id VARCHAR(50),
                    state VARCHAR(50),
                    operation VARCHAR(50),
                    container_state VARCHAR(50),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
            """)
            
            # 초기 상태 데이터 생성
            cursor.execute("""
                INSERT IGNORE INTO gate_status (gate_id, state, operation)
                VALUES ('GATE_A', 'CLOSED', 'IDLE')
            """)
            
            cursor.execute("""
                INSERT IGNORE INTO gate_status (gate_id, state, operation)
                VALUES ('GATE_B', 'CLOSED', 'IDLE')
            """)
            
            cursor.execute("""
                INSERT IGNORE INTO belt_status (belt_id, state, operation, container_state)
                VALUES ('BELT', 'STOPPED', 'IDLE', 'EMPTY')
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            print("[DEBUG] 시설 상태 데이터베이스 초기화 완료")
        
        except mysql.connector.Error as err:
            print(f"[ERROR] 시설 DB 초기화 실패: {err}")

    def reset_all_statuses(self):
        """모든 시설 상태 기록 초기화"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM gate_status")
            cursor.execute("DELETE FROM belt_status")
            conn.commit()
            cursor.close()
            conn.close()
            print("[✅ 시설 상태 초기화 완료] 모든 시설 상태 기록이 삭제되었습니다")
        except mysql.connector.Error as err:
            print(f"[ERROR] 시설 상태 초기화 실패: {err}")

    # 게이트 상태 로깅
    def log_gate_status(self, gate_id: str, state: str, operation: str):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO gate_status (gate_id, state, operation)
                VALUES (%s, %s, %s)
            """, (gate_id, state, operation))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[DEBUG] 게이트 상태 로깅 완료: {gate_id} - state={state}, operation={operation}")
        except mysql.connector.Error as err:
            print(f"[ERROR] 게이트 상태 로깅 실패: {err}")

    # 벨트 상태 로깅
    def log_belt_status(self, belt_id: str, state: str, operation: str, container_state: str):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO belt_status (belt_id, state, operation, container_state)
                VALUES (%s, %s, %s, %s)
            """, (belt_id, state, operation, container_state))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"[DEBUG] 벨트 상태 로깅 완료: {belt_id} - state={state}, operation={operation}, container={container_state}")
        except mysql.connector.Error as err:
            print(f"[ERROR] 벨트 상태 로깅 실패: {err}")

    # 게이트 최신 상태 조회
    def get_latest_gate_status(self, gate_id: str) -> Optional[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT gate_id, state, operation, timestamp
                FROM gate_status
                WHERE gate_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (gate_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row if row else None
        except mysql.connector.Error as err:
            print(f"[ERROR] 게이트 상태 조회 실패: {err}")
            return None

    # 벨트 최신 상태 조회
    def get_latest_belt_status(self, belt_id: str) -> Optional[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT belt_id, state, operation, container_state, timestamp
                FROM belt_status
                WHERE belt_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (belt_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row if row else None
        except mysql.connector.Error as err:
            print(f"[ERROR] 벨트 상태 조회 실패: {err}")
            return None

    # 게이트 상태 히스토리 조회
    def get_gate_history(self, gate_id: str, limit: int = 100) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT gate_id, state, operation, timestamp
                FROM gate_status
                WHERE gate_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (gate_id, limit))
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
        except mysql.connector.Error as err:
            print(f"[ERROR] 게이트 히스토리 조회 실패: {err}")
            return []

    # 벨트 상태 히스토리 조회
    def get_belt_history(self, belt_id: str, limit: int = 100) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT belt_id, state, operation, container_state, timestamp
                FROM belt_status
                WHERE belt_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (belt_id, limit))
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
        except mysql.connector.Error as err:
            print(f"[ERROR] 벨트 히스토리 조회 실패: {err}")
            return []

    def close(self):
        print("[DEBUG] FacilityStatusDB 리소스 정리 완료")
