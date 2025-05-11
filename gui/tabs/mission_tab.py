from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QComboBox, QLineEdit, QSpinBox, QRadioButton, QButtonGroup, QLabel, QVBoxLayout, QMessageBox, QHeaderView
from PyQt6.QtCore import QRect
from PyQt6 import uic
import os
from gui.api_client import api_client


class MissionTab(QWidget):
    """미션 관리 탭 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 파일 로드
        ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "tab_mission.ui")
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            print(f"[경고] UI 파일을 찾을 수 없습니다: {ui_path}")
            
        # 초기화
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        # 미션 추가 버튼 이벤트 연결
        add_button = self.findChild(QWidget, "pushButton_add_for_add")
        if add_button:
            add_button.clicked.connect(self.add_mission)
        else:
            print("[경고] 'pushButton_add_for_add' 버튼을 찾을 수 없습니다")
        
        # 미션 새로고침 버튼 이벤트 연결
        refresh_button = self.findChild(QWidget, "pushButton_refresh")
        if refresh_button:
            refresh_button.clicked.connect(self.refresh_mission_table)
        else:
            print("[경고] 'pushButton_refresh' 버튼을 찾을 수 없습니다")
            
        # 미션 삭제 버튼 이벤트 연결
        delete_button = self.findChild(QWidget, "pushButton_delete_selected")
        if delete_button:
            delete_button.clicked.connect(self.delete_selected_mission)
        else:
            print("[경고] 'pushButton_delete_selected' 버튼을 찾을 수 없습니다")
            
        # 모두 완료 처리 버튼 이벤트 연결
        complete_all_button = self.findChild(QWidget, "pushButton_complete_all")
        if complete_all_button:
            complete_all_button.clicked.connect(self.complete_all_missions)
        else:
            print("[경고] 'pushButton_complete_all' 버튼을 찾을 수 없습니다")
            
        # 상태 필터 체크박스 변경 이벤트 연결
        status_checkboxes = [
            "checkBox_waiting_for_search",
            "checkBox_assigned_for_search",
            "checkBox_completed_for_search",
            "checkBox_canceled_for_search",
            "checkBox_error_for_search"
        ]
        
        for checkbox_name in status_checkboxes:
            checkbox = self.findChild(QWidget, checkbox_name)
            if checkbox:
                checkbox.stateChanged.connect(self.auto_refresh_missions)
        
        # 출발지 및 트럭 콤보박스 변경 이벤트 연결
        source_combo = self.findChild(QWidget, "comboBox_source_for_search")
        if source_combo:
            source_combo.currentIndexChanged.connect(self.auto_refresh_missions)
            
        truck_combo = self.findChild(QWidget, "comboBox_truck_id_for_search")
        if truck_combo:
            truck_combo.currentIndexChanged.connect(self.auto_refresh_missions)
            
        # 미션 테이블 참조
        self.tablewidget = self.findChild(QWidget, "tableWidget_mission")
        
        # 디버깅: 테이블 위젯 존재 여부 확인
        if not self.tablewidget:
            print("[경고] 'tableWidget_mission' 테이블을 찾을 수 없습니다")
            # UI에 있는 모든 위젯 이름 출력
            for child in self.findChildren(QWidget):
                if hasattr(child, 'objectName'):
                    print(f"[디버그] 발견된 위젯: {child.objectName()}")
        else:
            print("[정보] 테이블 위젯을 찾았습니다")
            
        # 미션 테이블 설정
        if self.tablewidget:
            # 테이블 헤더 설정
            self.tablewidget.setColumnCount(11)
            self.tablewidget.setHorizontalHeaderLabels([
                "미션 ID", "화물 종류", "화물 양", "출발지", "목적지", 
                "상태 코드", "상태 레이블", "할당 트럭", "생성 시간", "할당 시간", "완료 시간"
            ])
            
            # 헤더 자동 크기 조정
            header = self.tablewidget.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            
            # 초기 데이터 로드
            self.search_missions()
            
    def refresh_mission_table(self):
        """미션 테이블 데이터 갱신 (현재 필터 유지)"""
        if not hasattr(self, 'tablewidget') or not self.tablewidget:
            print("[오류] 테이블 위젯이 없어 미션 데이터를 표시할 수 없습니다")
            return
        
        # 현재 필터 설정을 유지한 채로 미션 데이터만 새로고침
        self.search_missions()

    def display_missions(self, missions):
        """미션 데이터를 테이블에 표시"""
        if not hasattr(self, 'tablewidget') or not self.tablewidget:
            return
            
        self.tablewidget.setRowCount(0)
        
        if not missions:
            # 검색 결과가 없는 경우 테이블 헤더 텍스트 업데이트
            self.tablewidget.setHorizontalHeaderItem(0, QTableWidgetItem(f"미션 ID (결과 없음)"))
            return
            
        # 검색 결과가 있는 경우 테이블 헤더 텍스트 업데이트 (미션 수 표시)
        self.tablewidget.setHorizontalHeaderItem(0, QTableWidgetItem(f"미션 ID ({len(missions)}개)"))
        
        for mission in missions:
            row_idx = self.tablewidget.rowCount()
            self.tablewidget.insertRow(row_idx)
            
            # 기본 정보 표시
            self.tablewidget.setItem(row_idx, 0, QTableWidgetItem(str(mission.get('mission_id', ''))))
            self.tablewidget.setItem(row_idx, 1, QTableWidgetItem(str(mission.get('cargo_type', ''))))
            self.tablewidget.setItem(row_idx, 2, QTableWidgetItem(str(mission.get('cargo_amount', ''))))
            self.tablewidget.setItem(row_idx, 3, QTableWidgetItem(str(mission.get('source', ''))))
            self.tablewidget.setItem(row_idx, 4, QTableWidgetItem(str(mission.get('destination', ''))))
            
            # 상태 처리
            status = mission.get('status', {})
            status_code = ''
            status_label = ''
            
            if isinstance(status, dict):
                status_code = status.get('code', '')
                status_label = status.get('label', '')
            elif isinstance(status, str):
                status_code = status
            else:
                status_code = str(status)
            
            self.tablewidget.setItem(row_idx, 5, QTableWidgetItem(status_code))
            if status_label:
                self.tablewidget.setItem(row_idx, 6, QTableWidgetItem(status_label))
            
            # 나머지 정보 표시
            self.tablewidget.setItem(row_idx, 7, QTableWidgetItem(str(mission.get('assigned_truck_id', ''))))
            self.tablewidget.setItem(row_idx, 8, QTableWidgetItem(str(mission.get('timestamp_created', ''))))
            self.tablewidget.setItem(row_idx, 9, QTableWidgetItem(str(mission.get('timestamp_assigned', ''))))
            self.tablewidget.setItem(row_idx, 10, QTableWidgetItem(str(mission.get('timestamp_completed', ''))))
            
        # 헤더 자동 크기 조정
        header = self.tablewidget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            
    def add_mission(self):
        """새 미션 추가"""
        try:
            # 미션 입력값 가져오기 - UI 파일의 위젯 이름 사용
            lineedit_type = self.findChild(QWidget, "lineEdit_type_for_add")
            if not lineedit_type:
                print("[경고] 'lineEdit_type_for_add' 필드를 찾을 수 없습니다")
                cargo_type = "기본 화물"
            else:
                cargo_type = lineedit_type.text() or "기본 화물"
                
            spinBox = self.findChild(QWidget, "spinBox_amount_for_add")
            if not spinBox:
                print("[경고] 'spinBox_amount_for_add' 스핀박스를 찾을 수 없습니다")
                cargo_amount = 1.0
            else:
                cargo_amount = float(spinBox.value())
                
            source_widget = self.findChild(QWidget, "comboBox_source_for_add")
            if not source_widget:
                print("[경고] 'comboBox_source_for_add' 콤보박스를 찾을 수 없습니다")
                source = "LOAD_A"
            else:
                source = source_widget.currentText()
                
            # 목적지는 UI에 없으므로 하드코딩
            destination = "BELT"
            
            # 미션 ID 생성 (UI에는 없으므로 현재 시간 기반으로 생성)
            from datetime import datetime
            mission_id = f"mission_{datetime.now().strftime('%y%m%d_%H%M%S')}"
            
            # 입력값 검증
            if not cargo_type or cargo_amount <= 0 or not source or not destination:
                QMessageBox.warning(self, "입력 오류", "모든 필드를 올바르게 입력해주세요.")
                return
                
            if source == destination:
                QMessageBox.warning(self, "입력 오류", "출발지와 목적지가 같을 수 없습니다.")
                return
                
            # 미션 데이터 생성
            mission_data = {
                "mission_id": mission_id,
                "cargo_type": cargo_type,
                "cargo_amount": cargo_amount,
                "source": source,
                "destination": destination
            }
            
            print(f"[정보] 미션 생성 시도: {mission_data}")
            
            # API로 미션 생성
            response = api_client.create_mission(mission_data)
            
            # 성공 메시지 표시
            QMessageBox.information(self, "미션 생성", f"미션 {mission_id}이(가) 성공적으로 생성되었습니다.")
            
            # 미션 테이블 갱신 (필터 유지)
            self.search_missions()
            
            # 입력 필드 초기화
            if lineedit_type:
                lineedit_type.clear()
                
            if spinBox:
                spinBox.setValue(1)
            
        except Exception as e:
            print(f"[ERROR] 미션 생성 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "오류", f"미션 생성 중 오류가 발생했습니다: {e}")
            
    def delete_selected_mission(self):
        """선택된 미션 삭제"""
        if not self.tablewidget:
            print("[오류] 테이블 위젯이 없어 미션을 삭제할 수 없습니다")
            return
            
        # 선택된 행 가져오기
        selected_rows = self.tablewidget.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "선택 오류", "삭제할 미션을 선택해주세요.")
            return
            
        # 선택된 행의 미션 ID 가져오기
        mission_id_items = [self.tablewidget.item(item.row(), 0) for item in selected_rows]
        unique_mission_ids = list(set([item.text() for item in mission_id_items if item is not None]))
        
        if not unique_mission_ids:
            QMessageBox.warning(self, "선택 오류", "삭제할 미션을 선택해주세요.")
            return
            
        # 삭제 확인 메시지 표시
        if len(unique_mission_ids) == 1:
            msg = f"미션 '{unique_mission_ids[0]}'을(를) 취소하시겠습니까?"
        else:
            msg = f"{len(unique_mission_ids)}개의 미션을 취소하시겠습니까?"
            
        reply = QMessageBox.question(self, "미션 취소", msg, 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # 선택된 미션 취소
            for mission_id in unique_mission_ids:
                try:
                    api_client.cancel_mission(mission_id)
                    print(f"[INFO] 미션 취소: {mission_id}")
                except Exception as e:
                    print(f"[ERROR] 미션 취소 중 오류 발생: {e}")
                    QMessageBox.critical(self, "오류", f"미션 '{mission_id}' 취소 중 오류가 발생했습니다: {e}")
            
            # 미션 테이블 갱신 (필터 유지)
            self.search_missions()
            QMessageBox.information(self, "미션 취소", "선택한 미션이 취소되었습니다.")
            
    def complete_all_missions(self):
        """모든 미션을 완료 처리"""
        if not self.tablewidget:
            print("[오류] 테이블 위젯이 없어 미션을 완료할 수 없습니다")
            return
        
        # 테이블에서 완료되지 않은 미션 ID 가져오기
        incomplete_mission_ids = []
        for row in range(self.tablewidget.rowCount()):
            status_item = self.tablewidget.item(row, 5)
            if status_item and status_item.text() in ["WAITING", "ASSIGNED"]:
                mission_id_item = self.tablewidget.item(row, 0)
                if mission_id_item:
                    incomplete_mission_ids.append(mission_id_item.text())
        
        # 완료할 미션이 없으면 메시지 표시 후 종료
        if not incomplete_mission_ids:
            QMessageBox.information(self, "완료 처리", "완료할 미션이 없습니다.")
            return
        
        # 완료 확인 메시지 표시
        reply = QMessageBox.question(
            self, 
            "미션 일괄 완료", 
            f"완료되지 않은 {len(incomplete_mission_ids)}개 미션을 모두 완료 처리하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 성공/실패 카운터
            success_count = 0
            error_count = 0
            
            # 모든 미션 완료 처리
            for mission_id in incomplete_mission_ids:
                try:
                    api_client.complete_mission(mission_id)
                    print(f"[INFO] 미션 완료 처리: {mission_id}")
                    success_count += 1
                except Exception as e:
                    print(f"[ERROR] 미션 완료 처리 중 오류 발생: {e}")
                    error_count += 1
            
            # 결과 메시지 생성
            if error_count == 0:
                result_msg = f"{success_count}개의 미션이 성공적으로 완료 처리되었습니다."
            else:
                result_msg = f"{success_count}개의 미션이 완료 처리되었습니다. (오류: {error_count}개)"
            
            # 결과 메시지 표시
            if error_count > 0:
                QMessageBox.warning(self, "완료 처리 결과", result_msg)
            else:
                QMessageBox.information(self, "완료 처리 결과", result_msg)
            
            # 미션 테이블 갱신 (필터 유지)
            self.search_missions() 

    def auto_refresh_missions(self):
        """필터 변경 시 자동으로 미션 리스트 새로고침"""
        self.search_missions()

    def search_missions(self):
        """미션 조회 조건에 따라 미션 필터링"""
        try:
            # 모든 미션 데이터 가져오기
            all_missions = api_client.get_all_missions()
            
            # 필터 조건 가져오기
            status_filters = []
            
            # 체크된 상태 필터 가져오기
            if self.findChild(QWidget, "checkBox_waiting_for_search").isChecked():
                status_filters.append("WAITING")
                
            if self.findChild(QWidget, "checkBox_assigned_for_search").isChecked():
                status_filters.append("ASSIGNED")
                
            if self.findChild(QWidget, "checkBox_completed_for_search").isChecked():
                status_filters.append("COMPLETED")
                
            if self.findChild(QWidget, "checkBox_canceled_for_search").isChecked():
                status_filters.append("CANCELED")
                
            if self.findChild(QWidget, "checkBox_error_for_search").isChecked():
                status_filters.append("ERROR")
                
            # 트럭 필터 가져오기
            truck_combo = self.findChild(QWidget, "comboBox_truck_id_for_search")
            selected_truck = truck_combo.currentText() if truck_combo else None
            
            # 출발지 필터 가져오기
            source_combo = self.findChild(QWidget, "comboBox_source_for_search")
            selected_source = source_combo.currentText() if source_combo else None
            
            # 필터링된 미션 리스트
            filtered_missions = []
            
            for mission in all_missions:
                # 상태 필터 적용
                status = mission.get('status', {})
                status_code = ''
                
                if isinstance(status, dict):
                    status_code = status.get('code', '')
                elif isinstance(status, str):
                    status_code = status
                else:
                    status_code = str(status)
                    
                if status_filters and status_code not in status_filters:
                    continue
                    
                # 트럭 필터 적용
                if selected_truck and selected_truck != "모든 트럭":
                    truck_id = mission.get('assigned_truck_id', '')
                    if str(truck_id) != selected_truck.replace("트럭 ", ""):
                        continue
                        
                # 출발지 필터 적용
                if selected_source and selected_source != "모든 출발지":
                    source = mission.get('source', '')
                    if source != selected_source:
                        continue
                        
                # 모든 필터를 통과한 미션 추가
                filtered_missions.append(mission)
                
            # 필터링된 미션 표시
            self.display_missions(filtered_missions)
            
        except Exception as e:
            print(f"[ERROR] 미션 조회 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "오류", f"미션 조회 중 오류가 발생했습니다: {e}") 