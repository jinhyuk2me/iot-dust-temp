from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QFileDialog
from PyQt6.QtCore import QDate, Qt
from PyQt6 import uic
import os
from datetime import datetime, timedelta


class EventLogTab(QWidget):
    """이벤트 로그 탭 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "tab_event_log.ui")
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            print(f"[경고] UI 파일을 찾을 수 없습니다: {ui_path}")
            
        # 초기화
        self.init_ui()
        self.log_data = []  # 로그 데이터 저장 리스트
        
    def init_ui(self):
        """UI 초기화"""
        # 날짜 설정
        today = QDate.currentDate()
        start_date = self.findChild(QWidget, "dateEdit_start")
        if start_date:
            start_date.setDate(today.addDays(-7))  # 일주일 전부터
            
        end_date = self.findChild(QWidget, "dateEdit_end")
        if end_date:
            end_date.setDate(today)  # 오늘까지
            
        # 버튼 이벤트 연결
        apply_filter = self.findChild(QWidget, "pushButton_apply_filter")
        if apply_filter:
            apply_filter.clicked.connect(self.apply_filter)
            
        refresh_log = self.findChild(QWidget, "pushButton_refresh_log")
        if refresh_log:
            refresh_log.clicked.connect(self.refresh_logs)
            
        export_log = self.findChild(QWidget, "pushButton_export_log")
        if export_log:
            export_log.clicked.connect(self.export_logs)
            
        clear_log = self.findChild(QWidget, "pushButton_clear_log")
        if clear_log:
            clear_log.clicked.connect(self.clear_logs)
            
        # 초기 로그 로드
        self.refresh_logs()
        
    def refresh_logs(self):
        """로그 데이터 새로고침"""
        # TODO: 실제 DB나 로그 파일에서 데이터 로드하는 코드 구현
        # 샘플 로그 데이터 생성
        self.log_data = self.generate_sample_logs()
        
        # 현재 필터 적용
        self.apply_filter()
        
    def apply_filter(self):
        """로그 필터 적용"""
        log_table = self.findChild(QWidget, "tableWidget_log")
        if not log_table:
            return
            
        # 필터 조건 가져오기
        log_level_combo = self.findChild(QWidget, "comboBox_log_level")
        start_date_edit = self.findChild(QWidget, "dateEdit_start")
        end_date_edit = self.findChild(QWidget, "dateEdit_end")
        
        log_level = log_level_combo.currentText() if log_level_combo else "모든 로그"
        start_date = start_date_edit.date().toPyDate() if start_date_edit else None
        end_date = end_date_edit.date().toPyDate() if end_date_edit else None
        
        # 필터링된 로그 표시
        filtered_logs = []
        for log in self.log_data:
            # 날짜 필터링
            log_date = datetime.strptime(log["timestamp"].split()[0], "%Y-%m-%d").date()
            if start_date and log_date < start_date:
                continue
            if end_date and log_date > end_date:
                continue
                
            # 로그 레벨 필터링
            if log_level != "모든 로그" and log["level"] != log_level:
                continue
                
            filtered_logs.append(log)
            
        # 테이블에 로그 표시
        log_table.setRowCount(0)
        for log in filtered_logs:
            row = log_table.rowCount()
            log_table.insertRow(row)
            
            log_table.setItem(row, 0, QTableWidgetItem(log["timestamp"]))
            log_table.setItem(row, 1, QTableWidgetItem(log["level"]))
            log_table.setItem(row, 2, QTableWidgetItem(log["source"]))
            log_table.setItem(row, 3, QTableWidgetItem(log["message"]))
        
        # 가장 최근 로그가 상단에 오도록 정렬
        log_table.sortItems(0, Qt.SortOrder.DescendingOrder)  # 내림차순 정렬 (최신순)
        
    def export_logs(self):
        """로그 내보내기"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "로그 내보내기",
            "",
            "CSV 파일 (*.csv);;모든 파일 (*)"
        )
        
        if not file_path:
            return
            
        # 로그 파일 저장
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # 헤더 작성
                f.write("시간,로그 레벨,소스,메시지\n")
                
                # 로그 데이터 작성
                for log in self.log_data:
                    f.write(f"{log['timestamp']},{log['level']},{log['source']},{log['message']}\n")
                    
            print(f"[성공] 로그를 {file_path} 파일로 내보냈습니다.")
        except Exception as e:
            print(f"[오류] 로그 내보내기 실패: {e}")
            
    def clear_logs(self):
        """로그 지우기"""
        log_table = self.findChild(QWidget, "tableWidget_log")
        if log_table:
            log_table.setRowCount(0)
        
        # 실제 DB에서도 로그를 지우는 로직이 필요하면 추가
        # 현재는 메모리에서만 제거
        self.log_data = []
        
    def generate_sample_logs(self):
        """샘플 로그 데이터 생성 (실제 구현 시 제거)"""
        logs = []
        sources = ["시스템", "네트워크", "트럭 제어", "미션 관리", "사용자 인증"]
        levels = ["정보", "경고", "오류", "긴급"]
        messages = [
            "시스템이 시작되었습니다.",
            "네트워크 연결이 불안정합니다.",
            "트럭 연결이 해제되었습니다.",
            "미션 완료: mission_230515_123456",
            "사용자 로그인: admin",
            "미션 실패: 시간 초과",
            "트럭 배터리 부족 경고 (30% 이하)",
            "DB 연결 오류",
            "시스템 종료 요청",
            "모든 미션이 완료되었습니다."
        ]
        
        # 현재 시간부터 30일 전까지의 로그 생성
        now = datetime.now()
        for i in range(100):  # 100개의 샘플 로그
            # 랜덤 시간
            random_time = now - timedelta(
                days=i // 5,  # 20일 분량
                hours=i % 24,
                minutes=(i * 7) % 60
            )
            timestamp = random_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 랜덤 로그 정보
            import random
            level = random.choice(levels)
            source = random.choice(sources)
            message = random.choice(messages)
            
            logs.append({
                "timestamp": timestamp,
                "level": level,
                "source": source,
                "message": message
            })
            
        return logs 