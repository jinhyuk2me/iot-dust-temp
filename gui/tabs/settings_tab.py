from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QMessageBox
from PyQt6 import uic
import os
import mysql.connector


class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "tab_settings.ui")
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            print(f"[경고] UI 파일을 찾을 수 없습니다: {ui_path}")
            
        # DB 연결 정보 - 초기값
        self.db_config = {
            "host": "localhost",
            "user": "root",
            "password": "jinhyuk2dacibul",
            "database": "dust"
        }
        
        # 설정 저장용
        self.settings = {}
        
        # 초기화
        self.init_ui()
        self.load_settings()
        
    def get_db_connection(self):
        """DB 연결 가져오기"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            return conn
        except mysql.connector.Error as err:
            print(f"[ERROR] DB 연결 실패: {err}")
            return None
            
    def init_ui(self):
        """UI 초기화"""
        # 설정 관련 버튼 이벤트 연결
        save_button = self.findChild(QWidget, "pushButton_save_settings")
        if save_button:
            save_button.clicked.connect(self.save_settings)
            
        reset_button = self.findChild(QWidget, "pushButton_reset_settings")
        if reset_button:
            reset_button.clicked.connect(self.reset_settings)
            
        # 연결 테스트 버튼
        test_button = self.findChild(QWidget, "pushButton_test_connection")
        if test_button:
            test_button.clicked.connect(self.test_connection)
            
        # 네트워크 설정 적용 버튼
        apply_network = self.findChild(QWidget, "pushButton_apply_network")
        if apply_network:
            apply_network.clicked.connect(self.apply_network_settings)
            
        # 사용자 관리 버튼
        add_user_button = self.findChild(QWidget, "pushButton_add_user")
        if add_user_button:
            add_user_button.clicked.connect(self.add_user)
            
        edit_user_button = self.findChild(QWidget, "pushButton_edit_user")
        if edit_user_button:
            edit_user_button.clicked.connect(self.edit_user)
            
        delete_user_button = self.findChild(QWidget, "pushButton_delete_user")
        if delete_user_button:
            delete_user_button.clicked.connect(self.delete_user)
            
        # 사용자 테이블 로드
        self.load_users()
            
    def ensure_settings_table(self):
        """설정 테이블이 없으면 생성"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            # 설정 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    section VARCHAR(50) NOT NULL,
                    key_name VARCHAR(50) NOT NULL,
                    value TEXT,
                    UNIQUE KEY unique_setting (section, key_name)
                )
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except mysql.connector.Error as err:
            print(f"[ERROR] 설정 테이블 생성 실패: {err}")
            return False
            
    def load_settings(self):
        """데이터베이스에서 설정 로드"""
        try:
            # 설정 테이블 확인/생성
            if not self.ensure_settings_table():
                self.settings = self.get_default_settings()
                return
                
            conn = self.get_db_connection()
            if not conn:
                self.settings = self.get_default_settings()
                return
                
            cursor = conn.cursor(dictionary=True)
            
            # 모든 설정 로드
            cursor.execute("SELECT section, key_name, value FROM settings")
            rows = cursor.fetchall()
            
            # 결과가 없으면 기본값 사용
            if not rows:
                self.settings = self.get_default_settings()
                return
                
            # 설정 딕셔너리로 변환
            settings = {}
            for row in rows:
                section = row['section']
                key = row['key_name']
                value = row['value']
                
                # 값 타입 변환
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.isdigit():
                    value = int(value)
                    
                # 섹션이 없으면 생성
                if section not in settings:
                    settings[section] = {}
                    
                # 설정 저장
                settings[section][key] = value
                
            # 중첩 설정 적용 (예: network.server_address)
            self.settings = {}
            for section, values in settings.items():
                # 최상위 섹션인 경우 (예: theme, language)
                if '.' not in section:
                    if section not in self.settings:
                        self.settings[section] = {}
                        
                    for key, value in values.items():
                        self.settings[section][key] = value
                else:
                    # 중첩 섹션인 경우 처리
                    parts = section.split('.')
                    current = self.settings
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = values
            
            # 기본 설정과 병합 (누락된 설정 채우기)
            default_settings = self.get_default_settings()
            self.merge_settings(self.settings, default_settings)
            
            cursor.close()
            conn.close()
            
            # UI에 설정값 적용
            self.apply_settings_to_ui()
        except Exception as e:
            print(f"[오류] 설정 로드 실패: {e}")
            self.settings = self.get_default_settings()
            
    def merge_settings(self, target, source):
        """누락된 설정 채우기"""
        for key, value in source.items():
            if key not in target:
                target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                self.merge_settings(target[key], value)
            
    def apply_settings_to_ui(self):
        """설정값을 UI에 적용"""
        # 일반 설정
        theme_combo = self.findChild(QWidget, "comboBox_theme")
        if theme_combo and 'theme' in self.settings:
            index = theme_combo.findText(self.settings['theme'])
            if index >= 0:
                theme_combo.setCurrentIndex(index)
                
        lang_combo = self.findChild(QWidget, "comboBox_language")
        if lang_combo and 'language' in self.settings:
            index = lang_combo.findText(self.settings['language'])
            if index >= 0:
                lang_combo.setCurrentIndex(index)
                
        auto_update_check = self.findChild(QWidget, "checkBox_auto_update")
        if auto_update_check and 'auto_update' in self.settings:
            auto_update_check.setChecked(self.settings['auto_update'])
            
        # 네트워크 설정
        if 'network' in self.settings:
            network = self.settings['network']
            
            server_address = self.findChild(QWidget, "lineEdit_server_address")
            if server_address and 'server_address' in network:
                server_address.setText(network['server_address'])
                
            api_port = self.findChild(QWidget, "lineEdit_api_port")
            if api_port and 'api_port' in network:
                api_port.setText(str(network['api_port']))
                
            tcp_port = self.findChild(QWidget, "lineEdit_tcp_port")
            if tcp_port and 'tcp_port' in network:
                tcp_port.setText(str(network['tcp_port']))
                
        # DB 설정
        if 'database' in self.settings:
            db = self.settings['database']
            
            db_host = self.findChild(QWidget, "lineEdit_db_host")
            if db_host and 'host' in db:
                db_host.setText(db['host'])
                
            db_port = self.findChild(QWidget, "lineEdit_db_port")
            if db_port and 'port' in db:
                db_port.setText(str(db['port']))
                
            db_user = self.findChild(QWidget, "lineEdit_db_user")
            if db_user and 'user' in db:
                db_user.setText(db['user'])
                
            db_name = self.findChild(QWidget, "lineEdit_db_name")
            if db_name and 'database' in db:
                db_name.setText(db['database'])
                
            # 비밀번호는 보안상 마스킹 처리
            db_password = self.findChild(QWidget, "lineEdit_db_password")
            if db_password and 'password' in db:
                db_password.setText("●●●●●●●●●●")
            
    def get_default_settings(self):
        """기본 설정값 반환"""
        return {
            "theme": "라이트 모드",
            "language": "한국어",
            "auto_update": True,
            "network": {
                "server_address": "localhost",
                "api_port": 5001,
                "tcp_port": 9000
            },
            "database": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "jinhyuk2dacibul",
                "database": "dust"
            }
        }
        
    def gather_settings_from_ui(self):
        """UI에서 설정값 수집"""
        settings = {}
        
        # 일반 설정
        theme_combo = self.findChild(QWidget, "comboBox_theme")
        if theme_combo:
            settings['theme'] = theme_combo.currentText()
            
        lang_combo = self.findChild(QWidget, "comboBox_language")
        if lang_combo:
            settings['language'] = lang_combo.currentText()
            
        auto_update_check = self.findChild(QWidget, "checkBox_auto_update")
        if auto_update_check:
            settings['auto_update'] = auto_update_check.isChecked()
            
        # 네트워크 설정
        settings['network'] = {}
        
        server_address = self.findChild(QWidget, "lineEdit_server_address")
        if server_address:
            settings['network']['server_address'] = server_address.text()
            
        api_port = self.findChild(QWidget, "lineEdit_api_port")
        if api_port:
            try:
                settings['network']['api_port'] = int(api_port.text())
            except ValueError:
                settings['network']['api_port'] = 5001
                
        tcp_port = self.findChild(QWidget, "lineEdit_tcp_port")
        if tcp_port:
            try:
                settings['network']['tcp_port'] = int(tcp_port.text())
            except ValueError:
                settings['network']['tcp_port'] = 9000
                
        # DB 설정
        settings['database'] = {}
        
        db_host = self.findChild(QWidget, "lineEdit_db_host")
        if db_host:
            settings['database']['host'] = db_host.text()
            
        db_port = self.findChild(QWidget, "lineEdit_db_port")
        if db_port:
            try:
                settings['database']['port'] = int(db_port.text())
            except ValueError:
                settings['database']['port'] = 3306
                
        db_user = self.findChild(QWidget, "lineEdit_db_user")
        if db_user:
            settings['database']['user'] = db_user.text()
            
        db_password = self.findChild(QWidget, "lineEdit_db_password")
        if db_password and not db_password.text().startswith("●"):
            # 비밀번호가 변경된 경우만 저장
            settings['database']['password'] = db_password.text()
        elif 'database' in self.settings and 'password' in self.settings['database']:
            # 기존 비밀번호 유지
            settings['database']['password'] = self.settings['database']['password']
            
        db_name = self.findChild(QWidget, "lineEdit_db_name")
        if db_name:
            settings['database']['database'] = db_name.text()
            
        return settings
        
    def save_settings_to_db(self, settings):
        """설정을 DB에 저장"""
        try:
            # 설정 테이블 확인/생성
            if not self.ensure_settings_table():
                return False
                
            conn = self.get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            # 설정 저장 함수
            def save_setting(section, key, value):
                # 값 타입 변환
                if isinstance(value, bool):
                    value = str(value).lower()
                else:
                    value = str(value)
                
                cursor.execute("""
                    INSERT INTO settings (section, key_name, value)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE value = %s
                """, (section, key, value, value))
            
            # 중첩 설정 저장 함수
            def save_nested_settings(prefix, data):
                for key, value in data.items():
                    if isinstance(value, dict):
                        # 중첩 딕셔너리
                        new_prefix = f"{prefix}.{key}" if prefix else key
                        save_nested_settings(new_prefix, value)
                    else:
                        # 일반 값
                        save_setting(prefix, key, value)
                        
            # 설정 저장
            save_nested_settings("", settings)
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except mysql.connector.Error as err:
            print(f"[ERROR] 설정 저장 실패: {err}")
            return False
        
    def save_settings(self):
        """설정 저장"""
        try:
            # UI에서 설정값 수집
            self.settings = self.gather_settings_from_ui()
            
            # DB에 설정 저장
            if self.save_settings_to_db(self.settings):
                QMessageBox.information(self, "설정 저장", "설정이 데이터베이스에 저장되었습니다.")
            else:
                QMessageBox.critical(self, "오류", "데이터베이스에 설정을 저장하지 못했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 저장 중 오류가 발생했습니다: {e}")
            
    def reset_settings(self):
        """설정 초기화"""
        reply = QMessageBox.question(
            self, 
            "설정 초기화", 
            "모든 설정을 기본값으로 되돌리시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings = self.get_default_settings()
            self.apply_settings_to_ui()
            
            # DB에 설정 저장
            if self.save_settings_to_db(self.settings):
                QMessageBox.information(self, "설정 초기화", "설정이 초기화되었습니다.")
            else:
                QMessageBox.critical(self, "오류", "설정 초기화 중 오류가 발생했습니다.")
            
    def test_connection(self):
        """DB 연결 테스트"""
        # DB 설정 수집
        db_settings = {}
        
        db_host = self.findChild(QWidget, "lineEdit_db_host")
        if db_host:
            db_settings['host'] = db_host.text()
            
        db_port = self.findChild(QWidget, "lineEdit_db_port")
        if db_port:
            try:
                db_settings['port'] = int(db_port.text())
            except ValueError:
                db_settings['port'] = 3306
                
        db_user = self.findChild(QWidget, "lineEdit_db_user")
        if db_user:
            db_settings['user'] = db_user.text()
            
        db_password = self.findChild(QWidget, "lineEdit_db_password")
        if db_password:
            # 마스킹된 비밀번호면 기존 설정에서 가져옴
            if db_password.text().startswith("●"):
                if 'database' in self.settings and 'password' in self.settings['database']:
                    db_settings['password'] = self.settings['database']['password']
            else:
                db_settings['password'] = db_password.text()
                
        db_name = self.findChild(QWidget, "lineEdit_db_name")
        if db_name:
            db_settings['database'] = db_name.text()
            
        # 연결 테스트
        try:
            # 실제 DB 연결 테스트
            conn = mysql.connector.connect(**db_settings)
            conn.close()
            
            QMessageBox.information(self, "연결 테스트", "데이터베이스 연결에 성공했습니다.")
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "연결 오류", f"데이터베이스 연결에 실패했습니다: {e}")
            
    def apply_network_settings(self):
        """네트워크 설정 적용"""
        # 네트워크 설정 수집
        network_settings = {}
        
        server_address = self.findChild(QWidget, "lineEdit_server_address")
        if server_address:
            network_settings['server_address'] = server_address.text()
            
        api_port = self.findChild(QWidget, "lineEdit_api_port")
        if api_port:
            try:
                network_settings['api_port'] = int(api_port.text())
            except ValueError:
                network_settings['api_port'] = 5001
                
        tcp_port = self.findChild(QWidget, "lineEdit_tcp_port")
        if tcp_port:
            try:
                network_settings['tcp_port'] = int(tcp_port.text())
            except ValueError:
                network_settings['tcp_port'] = 9000
                
        # 설정 저장
        if 'network' not in self.settings:
            self.settings['network'] = {}
            
        self.settings['network'].update(network_settings)
        
        # API 클라이언트 설정 업데이트
        try:
            from gui.api_client import api_client
            api_client.update_config(
                server_address=network_settings.get('server_address'),
                api_port=network_settings.get('api_port')
            )
            print(f"[INFO] API 클라이언트 설정 업데이트: {network_settings.get('server_address')}:{network_settings.get('api_port')}")
        except Exception as e:
            print(f"[ERROR] API 클라이언트 설정 업데이트 실패: {e}")
        
        # DB에 설정 저장
        if self.save_settings_to_db({"network": network_settings}):
            QMessageBox.information(self, "설정 적용", "네트워크 설정이 적용되었습니다.")
        else:
            QMessageBox.critical(self, "오류", "네트워크 설정 적용 중 오류가 발생했습니다.")
        
    def load_users(self):
        """사용자 목록 로드"""
        users_table = self.findChild(QWidget, "tableWidget_users")
        if not users_table:
            return
            
        # 테이블 초기화
        users_table.setRowCount(0)
        
        try:
            # DB에서 사용자 로드
            conn = self.get_db_connection()
            if not conn:
                # 샘플 데이터로 대체
                self.load_sample_users(users_table)
                return
                
            cursor = conn.cursor(dictionary=True)
            
            # 사용자 테이블이 있는지 확인
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = 'users'
            """, (self.db_config["database"],))
            
            if cursor.fetchone()['COUNT(*)'] == 0:
                # 테이블이 없으면 샘플 데이터로 대체
                cursor.close()
                conn.close()
                self.load_sample_users(users_table)
                return
            
            # 사용자 로드 - name 칼럼이 없으므로 username을 대신 사용하고, last_login도 제거
            cursor.execute("""
                SELECT id, username, role
                FROM users
                ORDER BY id DESC
            """)
            
            users = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # 테이블에 표시
            for user in users:
                row = users_table.rowCount()
                users_table.insertRow(row)
                
                users_table.setItem(row, 0, QTableWidgetItem(user["username"]))
                users_table.setItem(row, 1, QTableWidgetItem(user["username"]))  # name 대신 username 사용
                users_table.setItem(row, 2, QTableWidgetItem(user["role"]))
                users_table.setItem(row, 3, QTableWidgetItem("-"))  # last_login 정보 없음
                
        except mysql.connector.Error as err:
            print(f"[ERROR] 사용자 로드 실패: {err}")
            self.load_sample_users(users_table)
            
    def load_sample_users(self, users_table):
        """샘플 사용자 정보 로드"""
        # 샘플 사용자 정보
        sample_users = [
            {"username": "admin", "name": "관리자", "role": "admin", "last_login": "2023-05-15 09:30:22"},
            {"username": "operator1", "name": "운영자1", "role": "operator", "last_login": "2023-05-15 08:45:10"},
            {"username": "operator2", "name": "운영자2", "role": "operator", "last_login": "2023-05-14 17:22:05"}
        ]
        
        # 테이블에 사용자 정보 표시
        for user in sample_users:
            row = users_table.rowCount()
            users_table.insertRow(row)
            
            users_table.setItem(row, 0, QTableWidgetItem(user["username"]))
            users_table.setItem(row, 1, QTableWidgetItem(user["name"]))
            users_table.setItem(row, 2, QTableWidgetItem(user["role"]))
            users_table.setItem(row, 3, QTableWidgetItem(user["last_login"]))
            
    def add_user(self):
        """사용자 추가"""
        # TODO: 사용자 추가 대화상자 구현
        QMessageBox.information(self, "사용자 추가", "사용자 추가 기능은 아직 구현되지 않았습니다.")
        
    def edit_user(self):
        """사용자 편집"""
        users_table = self.findChild(QWidget, "tableWidget_users")
        if not users_table:
            return
            
        selected_row = users_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "사용자 편집", "편집할 사용자를 선택하세요.")
            return
            
        username = users_table.item(selected_row, 0).text()
        # TODO: 사용자 편집 대화상자 구현
        QMessageBox.information(self, "사용자 편집", f"사용자 '{username}' 편집 기능은 아직 구현되지 않았습니다.")
        
    def delete_user(self):
        """사용자 삭제"""
        users_table = self.findChild(QWidget, "tableWidget_users")
        if not users_table:
            return
            
        selected_row = users_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "사용자 삭제", "삭제할 사용자를 선택하세요.")
            return
            
        username = users_table.item(selected_row, 0).text()
        
        reply = QMessageBox.question(
            self, 
            "사용자 삭제", 
            f"사용자 '{username}'을(를) 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # DB에서 사용자 삭제
                conn = self.get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM users WHERE username = %s", (username,))
                    conn.commit()
                    cursor.close()
                    conn.close()
                
                # 테이블에서 삭제
                users_table.removeRow(selected_row)
                QMessageBox.information(self, "사용자 삭제", f"사용자 '{username}'이(가) 삭제되었습니다.")
            except mysql.connector.Error as err:
                print(f"[ERROR] 사용자 삭제 실패: {err}")
                QMessageBox.critical(self, "오류", f"사용자 삭제 중 오류가 발생했습니다: {err}") 