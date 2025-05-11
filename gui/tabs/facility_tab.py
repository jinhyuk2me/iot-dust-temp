from PyQt6.QtWidgets import QWidget, QMessageBox, QScrollBar
from PyQt6 import uic
import os
from gui.api_client import api_client


class FacilityTab(QWidget):
    """시설 제어 탭 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "tab_facility.ui")
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            print(f"[경고] UI 파일을 찾을 수 없습니다: {ui_path}")
            
        # 게이트 상태 추적을 위한 변수
        self.gate_status = {
            "GATE_A": "closed",
            "GATE_B": "closed"
        }
        
        # 벨트 상태 추적
        self.belt_status = "stopped"
            
        # 초기화
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        # 벨트 제어 버튼 이벤트 연결 (일반 클릭 방식)
        belt_start = self.findChild(QWidget, "pushButton_belt_start")
        if belt_start:
            belt_start.clicked.connect(self.toggle_belt)
            
        # 게이트 제어 버튼 이벤트 연결 (클릭 방식으로 변경)
        gate_a_open = self.findChild(QWidget, "pushButton_gate_a_open")
        if gate_a_open:
            gate_a_open.clicked.connect(lambda: self.toggle_gate("GATE_A"))
            
        gate_b_open = self.findChild(QWidget, "pushButton_gate_b_open")
        if gate_b_open:
            gate_b_open.clicked.connect(lambda: self.toggle_gate("GATE_B"))
            
        # 로그 관련 버튼 이벤트 연결
        clear_log_button = self.findChild(QWidget, "pushButton_clear_log")
        if clear_log_button:
            clear_log_button.clicked.connect(self.clear_log)
            
        refresh_status_button = self.findChild(QWidget, "pushButton_refresh_status")
        if refresh_status_button:
            refresh_status_button.clicked.connect(self.refresh_status)
            
        export_log_button = self.findChild(QWidget, "pushButton_export_log")
        if export_log_button:
            export_log_button.clicked.connect(self.export_log)
            
        refresh_log_button = self.findChild(QWidget, "pushButton_refresh_log")
        if refresh_log_button:
            refresh_log_button.clicked.connect(self.refresh_log)
        
        # 초기 상태 정보 표시
        self.refresh_status()
        
    def toggle_belt(self):
        """벨트 토글 (시작/정지) - 체크 상태 없이 텍스트만 변경"""
        try:
            button = self.findChild(QWidget, "pushButton_belt_start")
            
            if self.belt_status == "stopped":  # 벨트 시작
                response = api_client.control_belt("BELT", "start", 100)
                self.belt_status = "running"
                self.log_facility_action("벨트 시작")
                print("[INFO] 벨트 시작")
                if button:
                    button.setText("가동 정지")
            else:  # 벨트 정지
                response = api_client.control_belt("BELT", "stop")
                self.belt_status = "stopped"
                self.log_facility_action("벨트 정지")
                print("[INFO] 벨트 정지")
                if button:
                    button.setText("가동 시작")
                    
            # 상태 정보 업데이트
            self.update_facility_status()
                
        except Exception as e:
            error_msg = f"벨트 제어 실패: {e}"
            self.log_facility_action(f"오류: {error_msg}")
            print(f"[ERROR] {error_msg}")
            QMessageBox.critical(self, "오류", error_msg)
    
    def toggle_gate(self, gate_id):
        """게이트 상태 토글"""
        try:
            # 버튼 참조 얻기
            button_name = f"pushButton_gate_{gate_id.lower().split('_')[1]}_open"
            button = self.findChild(QWidget, button_name)
            
            # 현재 상태 확인 및 반대 명령 생성
            current_status = self.gate_status.get(gate_id, "closed")
            command = "close" if current_status == "open" else "open"
            
            # API 호출
            response = api_client.control_gate(gate_id, command)
            
            # 상태 업데이트
            self.gate_status[gate_id] = command
            
            # 로그 기록
            action = "열기" if command == "open" else "닫기"
            self.log_facility_action(f"게이트 {gate_id} {action}")
            print(f"[INFO] 게이트 {gate_id} {action}")
            
            # 버튼 텍스트 업데이트
            if button:
                button.setText(f"게이트 {gate_id.split('_')[1]} {'닫기' if command == 'open' else '열기'}")
                
            # 상태 정보 업데이트
            self.update_facility_status()
            
        except Exception as e:
            error_msg = f"게이트 {gate_id} 제어 실패: {e}"
            self.log_facility_action(f"오류: {error_msg}")
            print(f"[ERROR] {error_msg}")
            QMessageBox.critical(self, "오류", error_msg)
            
            # 현재 게이트 상태에 맞게 버튼 텍스트 복원
            if button:
                current_status = self.gate_status.get(gate_id, "closed")
                is_open = (current_status == "open")
                button.setText(f"게이트 {gate_id.split('_')[1]} {'닫기' if is_open else '열기'}")
                
    def update_facility_status(self):
        """시설 상태 정보 업데이트"""
        text_browser = self.findChild(QWidget, "textBrowser_facility_status")
        if text_browser:
            # 상태 정보 텍스트 생성
            status_text = "<b>벨트 상태:</b> "
            status_text += "작동 중" if self.belt_status == "running" else "정지"
            status_text += "<br><br>"
            
            # 게이트 상태 추가
            for gate_id in ["GATE_A", "GATE_B"]:
                current_status = self.gate_status.get(gate_id, "closed")
                status_text += f"<b>게이트 {gate_id.split('_')[1]} 상태:</b> "
                status_text += "열림" if current_status == "open" else "닫힘"
                status_text += "<br>"
                
            # 상태 표시
            text_browser.setHtml(status_text)
        
    def log_facility_action(self, message):
        """시설 제어 로그 기록"""
        text_edit = self.findChild(QWidget, "textEdit_facilty_status_log")
        if text_edit:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text_edit.append(f"[{timestamp}] {message}")
            
            # 항상 마지막 로그가 보이도록 스크롤
            scroll_bar = text_edit.verticalScrollBar()
            if scroll_bar:
                scroll_bar.setValue(scroll_bar.maximum())
                
    def clear_log(self):
        """로그 내용 지우기"""
        text_edit = self.findChild(QWidget, "textEdit_facilty_status_log")
        if text_edit:
            text_edit.clear()
            self.log_facility_action("로그가 초기화되었습니다.")
            
    def refresh_log(self):
        """로그 새로고침"""
        self.log_facility_action("로그가 새로고침되었습니다.")
            
    def refresh_status(self):
        """시설 상태 정보 새로고침"""
        try:
            # 벨트 상태 표시
            belt_status = api_client.get_belt("BELT")
            status = belt_status.get("status", "unknown")
            self.belt_status = status
            
            # 벨트 버튼 텍스트 업데이트 (체크 상태 없이)
            belt_button = self.findChild(QWidget, "pushButton_belt_start")
            if belt_button:
                is_running = (status == "running")
                belt_button.setText("가동 정지" if is_running else "가동 시작")
                    
            # 게이트 상태 업데이트
            for gate_id in ["GATE_A", "GATE_B"]:
                gate_status = api_client.get_gate(gate_id)
                current_status = gate_status.get("status", "closed")
                
                # 상태 저장
                self.gate_status[gate_id] = current_status
                
                # 버튼 텍스트 업데이트
                button_name = f"pushButton_gate_{gate_id.lower().split('_')[1]}_open"
                button = self.findChild(QWidget, button_name)
                if button:
                    is_open = (current_status == "open")
                    button.setText(f"게이트 {gate_id.split('_')[1]} {'닫기' if is_open else '열기'}")
            
            # 상태 정보 업데이트
            self.update_facility_status()
                
            self.log_facility_action("시설 상태 정보가 갱신되었습니다.")
            
        except Exception as e:
            error_msg = f"상태 정보 갱신 실패: {e}"
            self.log_facility_action(f"오류: {error_msg}")
            print(f"[ERROR] {error_msg}")
            QMessageBox.critical(self, "오류", error_msg)
            
    def export_log(self):
        """로그를 파일로 내보내기"""
        from PyQt6.QtWidgets import QFileDialog
        import os
        
        try:
            text_edit = self.findChild(QWidget, "textEdit_facilty_status_log")
            if not text_edit:
                return
                
            # 현재 날짜, 시간으로 기본 파일명 생성
            from datetime import datetime
            default_filename = f"facility_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            # 파일 저장 대화상자 표시
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "로그 저장", 
                os.path.join(os.path.expanduser("~"), default_filename),
                "텍스트 파일 (*.txt);;모든 파일 (*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text_edit.toPlainText())
                self.log_facility_action(f"로그가 파일로 저장되었습니다: {file_path}")
                print(f"[INFO] 로그 저장 완료: {file_path}")
                
        except Exception as e:
            error_msg = f"로그 내보내기 실패: {e}"
            self.log_facility_action(f"오류: {error_msg}")
            print(f"[ERROR] {error_msg}")
            QMessageBox.critical(self, "오류", error_msg)