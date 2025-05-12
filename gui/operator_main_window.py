from PyQt6.QtWidgets import QMainWindow, QTabWidget
from PyQt6.QtCore import QTimer, QSize
from PyQt6 import uic

from gui.tabs.monitoring_tab import MonitoringTab
from gui.tabs.mission_tab import MissionTab

import os


class OperatorMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 기본 윈도우 UI 로드
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "main.ui")
        uic.loadUi(ui_path, self)
        self.setWindowTitle("지능형 운송관제 시스템 D.U.S.T. - 운영자 모드")
        
        # 메인 윈도우 크기 설정
        self.setMinimumSize(1220, 680)
        
        # 탭 위젯 참조
        self.tabWidget = self.findChild(QTabWidget, "tabWidget")
        
        # 탭 초기화 
        self.init_tabs()
        
        # 배터리 상태 업데이트 타이머
        self.battery_timer = QTimer()
        self.battery_timer.timeout.connect(self.refresh_battery_status)
        self.battery_timer.start(1000)

    def init_tabs(self):
        """탭 초기화 - 운영자는 모니터링과 미션 탭만 볼 수 있음"""
        if not self.tabWidget:
            print("[오류] 탭 위젯을 찾을 수 없습니다.")
            return
        
        # 탭 위젯 크기 설정
        self.tabWidget.setMinimumSize(1200, 635)
        
        # 기존 탭 모두 제거
        while self.tabWidget.count() > 0:
            self.tabWidget.removeTab(0)
            
        # 모니터링 탭
        self.monitoring_tab = MonitoringTab()
        self.tabWidget.addTab(self.monitoring_tab, "Main Monitoring")
        
        # 미션 관리 탭
        self.mission_tab = MissionTab()
        self.tabWidget.addTab(self.mission_tab, "Mission Management")
        
    def refresh_battery_status(self):
        """배터리 상태 업데이트"""
        if hasattr(self, 'monitoring_tab'):
            self.monitoring_tab.refresh_battery_status() 