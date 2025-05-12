from backend.serialio.device_manager import DeviceManager
from backend.serialio.belt_controller import BeltController
from backend.serialio.gate_controller import GateController

from backend.mission.mission_db import MissionDB
from backend.mission.mission_manager import MissionManager

from backend.truck_status.truck_status_db import TruckStatusDB
from backend.truck_status.truck_status_manager import TruckStatusManager

from backend.tcpio.truck_command_sender import TruckCommandSender
from backend.truck_fsm.truck_fsm_manager import TruckFSMManager
from backend.truck_fsm.truck_message_handler import TruckMessageHandler


class MainController:
    def __init__(self, port_map, use_fake=False, fake_devices=None, debug=False, facility_status_manager=None):
        # 디버그 모드 설정
        self.debug = debug
        
        # 시설 상태 관리자 저장
        self.facility_status_manager = facility_status_manager
        
        # Serial 연결 및 장치 컨트롤러 생성
        self.device_manager = DeviceManager(
            port_map=port_map, 
            use_fake=use_fake, 
            fake_devices=fake_devices, 
            debug=debug, 
            facility_status_manager=facility_status_manager
        )

        # Mission DB 초기화
        self.mission_db = MissionDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        self.mission_manager = MissionManager(self.mission_db)

        # TruckStatusDB 초기화
        self.status_db = TruckStatusDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        self.truck_status_manager = TruckStatusManager(self.status_db)

        # 장치 컨트롤러 가져오기
        self.belt_controller = self.device_manager.get_controller("BELT")
        
        # 게이트 컨트롤러들 참조
        self.gate_controllers = {
            gate_id: self.device_manager.get_controller(gate_id)
            for gate_id in ["GATE_A", "GATE_B"]
            if self.device_manager.get_controller(gate_id) is not None
        }
        
        # 대표 게이트 컨트롤러 (FSM용)
        if "GATE_A" in self.gate_controllers:
            self.gate_controller = self.gate_controllers["GATE_A"]
        elif "GATE_B" in self.gate_controllers:
            self.gate_controller = self.gate_controllers["GATE_B"]
        else:
            print("[⚠️ 경고] 사용 가능한 게이트 컨트롤러가 없습니다")
            self.gate_controller = None
        
        # FSM 관리자
        self.truck_fsm_manager = TruckFSMManager(
            gate_controller=self.gate_controller,
            mission_manager=self.mission_manager,
            belt_controller=self.belt_controller,
            truck_status_manager=self.truck_status_manager
        )

        # 트럭 메시지 핸들러
        self.truck_message_handler = TruckMessageHandler(self.truck_fsm_manager)
        self.truck_message_handler.set_status_manager(self.truck_status_manager)

        # 초기 TruckCommandSender 설정
        self.set_truck_commander({})

        print("[✅ MainController 초기화 완료]")

    # 트럭 명령 전송자 설정
    def set_truck_commander(self, truck_socket_map: dict):
        """트럭 명령 전송자 설정"""
        commander = TruckCommandSender(truck_socket_map)
        self.truck_fsm_manager.set_commander(commander)

    # 메시지 처리
    def handle_message(self, msg: dict):
        """메시지 처리"""
        sender = msg.get("sender")
        cmd = msg.get("cmd", "").strip().upper()
        payload = msg.get("payload", {})

        print(f"[📨 MainController] sender={sender}, cmd={cmd}")

        # 벨트 수동 제어
        if cmd.startswith("BELT_"):
            self._handle_manual_belt_command(cmd)
            return

        # 게이트 수동 제어
        if cmd.startswith("GATE_"):
            self._handle_manual_gate_command(cmd)
            return

        # 트럭 메시지 처리
        if sender:
            self.truck_message_handler.handle_message(msg)
        else:
            print("[⚠️ 경고] sender가 없는 메시지")

    # 수동 벨트 제어 명령 처리
    def _handle_manual_belt_command(self, cmd: str):
        """수동 벨트 제어"""
        print(f"[⚙️ 수동 벨트 제어] CMD: {cmd}")
        if self.belt_controller:
            self.belt_controller.handle_message(cmd)
        else:
            print("[❌ 오류] 벨트 컨트롤러를 찾을 수 없습니다")

    # 수동 게이트 제어 명령 처리
    def _handle_manual_gate_command(self, cmd: str):
        """수동 게이트 제어"""
        parts = cmd.split("_")
        if len(parts) == 3:
            gate_id = f"GATE_{parts[1]}"
            action = parts[2]
            
            gate_controller = self.gate_controllers.get(gate_id)
            if gate_controller:
                if action == "OPEN":
                    gate_controller.open_gate(gate_id)
                elif action == "CLOSE":
                    gate_controller.close_gate(gate_id)
            else:
                print(f"[❌ 오류] {gate_id} 컨트롤러를 찾을 수 없습니다")
        else:
            print(f"[❌ 게이트 명령 포맷 오류] {cmd}")

    # 시스템 종료
    def shutdown(self):
        """시스템 종료"""
        print("[🔌 시스템 종료 중...]")
        self.mission_db.close()
        self.status_db.close()
        self.device_manager.close_all()
        if self.facility_status_manager:
            self.facility_status_manager.close()
        print("[✅ 시스템 종료 완료]") 