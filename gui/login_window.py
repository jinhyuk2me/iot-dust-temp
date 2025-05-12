# gui/login_window.py

from PyQt6.QtWidgets import QMainWindow, QMessageBox, QLineEdit
from PyQt6 import uic
import os

from backend.auth.auth_manager import AuthManager
from gui.admin_main_window import AdminMainWindow
from gui.operator_main_window import OperatorMainWindow

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # UI 파일 경로
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "login.ui")
        uic.loadUi(ui_path, self)

        # 비밀번호 입력 필드 설정
        self.input_pw.setEchoMode(QLineEdit.EchoMode.Password)

        # DB 인증 관리자 설정
        self.auth_manager = AuthManager({
            "host": "localhost",
            "user": "root",
            "password": "jinhyuk2dacibul",
            "database": "dust"
        })

        # 로그인 버튼 이벤트 연결
        self.btn_login.clicked.connect(self.handle_login)
        self.input_pw.returnPressed.connect(self.handle_login)


    def handle_login(self):
        username = self.input_id.text().strip()
        password = self.input_pw.text().strip()

        success, role = self.auth_manager.verify_user(username, password)
        if success:
            self.open_main(role)
        else:
            QMessageBox.warning(self, "로그인 실패", "❌ 아이디 또는 비밀번호가 잘못되었습니다.")

    def open_main(self, role):
        # 로그인 성공 → 역할에 따라 적절한 메인 윈도우 열기
        if role == "admin" or role == "god":
            # 관리자나 god 권한인 경우 관리자 윈도우 열기
            self.main = AdminMainWindow()
        else:
            # 그 외 역할(operator)는 운영자 윈도우 열기
            self.main = OperatorMainWindow()
            
        self.main.show()
        self.close()
