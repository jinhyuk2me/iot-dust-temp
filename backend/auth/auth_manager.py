# backend/auth/auth_manager.py

import mysql.connector

class AuthManager:
    def __init__(self, db_config: dict):
        try:
            self.conn = mysql.connector.connect(**db_config)
            self.cursor = self.conn.cursor()
            print("[✅ DB 연결 성공]")
        except mysql.connector.Error as err:
            print(f"[❌ DB 연결 실패] {err}")
            raise

    # 사용자 인증
    def verify_user(self, username: str, password: str):
        query = "SELECT password, role FROM users WHERE username = %s"
        self.cursor.execute(query, (username,))
        row = self.cursor.fetchone()
        if row:
            stored_password, role = row
            if stored_password == password:
                print(f"[✅ 로그인 성공] {username} ({role})")
                return True, role
            else:
                print(f"[⚠️ 비밀번호 불일치] {username}")
        else:
            print(f"[❌ 사용자 없음] {username}")

        return False, None

    # 연결 종료
    def close(self):
        self.cursor.close()
        self.conn.close()
