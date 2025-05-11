# backend/serialio/device_manager.py

from .belt_controller import BeltController
from .gate_controller import GateController
from .serial_interface import SerialInterface
from typing import Dict, Type, Any, Optional, List
import serial
import time
import importlib

# FakeSerial 클래스 임포트
try:
    from .fake_serial import FakeSerial
except ImportError:
    class FakeSerial:
        def __init__(self, *args, **kwargs):
            self.buffer = ""
            print("[FakeSerial] 가상 시리얼 초기화")
        
        def write(self, data):
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            print(f"[FakeSerial] 전송: {data}")
            return len(data)
        
        def read_until(self, terminator=b'\n', timeout=None):
            return b"ACK:GATE_A_OPENED\n"
        
        def close(self):
            print("[FakeSerial] 연결 종료")


class DeviceManager:
    def __init__(self, port_map: dict, use_fake=False, fake_devices=None, debug=False, facility_status_manager=None):
        self.controllers = {}
        self.interfaces = {}
        self.use_fake = use_fake
        self.fake_devices = fake_devices or []
        self.debug = debug
        self.facility_status_manager = facility_status_manager
        
        if use_fake and not fake_devices:
            print(f"[DeviceManager] 시리얼 관리자 초기화 - 모든 장치 가상 모드")
        elif fake_devices:
            print(f"[DeviceManager] 시리얼 관리자 초기화 - 부분 가상 모드 ({', '.join(fake_devices)})")
        else:
            print(f"[DeviceManager] 시리얼 관리자 초기화 - 모든 장치 실제 모드")
            
        print(f"[DeviceManager] 포트 맵: {port_map}")
        print(f"[DeviceManager] 디버그 모드: {'활성화' if debug else '비활성화'}")
        
        # 포트별 장치 매핑 생성
        port_to_devices = {}
        for device_id, port in port_map.items():
            if port not in port_to_devices:
                port_to_devices[port] = []
            port_to_devices[port].append(device_id)
        
        # 중복 포트 로깅
        for port, devices in port_to_devices.items():
            if len(devices) > 1:
                print(f"[DeviceManager ⚠️] 포트 {port}에 여러 장치가 매핑됨: {devices}")
                
        # 모든 장치 컨트롤러 생성
        for device_id, port in port_map.items():
            device_use_fake = use_fake
            if fake_devices:
                device_use_fake = device_id in fake_devices
            
            controller = self.create_controller(device_id, port, device_use_fake)
            if controller:
                self.controllers[device_id] = controller
                print(f"[DeviceManager] {device_id} 컨트롤러 등록 완료 ({'가상' if device_use_fake else '실제'} 모드)")
        
        print(f"[DeviceManager] 등록된 컨트롤러: {list(self.controllers.keys())}")

    # 시리얼 인터페이스 생성 또는 재사용
    def get_or_create_interface(self, port: str, use_fake=False):
        key = f"{port}_{use_fake}"
        
        if key in self.interfaces:
            print(f"[DeviceManager] 기존 인터페이스 재사용: {port} ({'가상' if use_fake else '실제'} 모드)")
            return self.interfaces[key]
        
        # 새 인터페이스 생성 (디버그 모드 전달)
        interface = SerialInterface(port, use_fake=use_fake, debug=self.debug)
        self.interfaces[key] = interface
        print(f"[DeviceManager] 새 인터페이스 생성: {port} ({'가상' if use_fake else '실제'} 모드)")
        return interface
    
    # 장치 컨트롤러 생성
    def create_controller(self, device_id: str, port: str, use_fake=False):
        print(f"[DeviceManager] 컨트롤러 생성: {device_id} → {port} ({'가상' if use_fake else '실제'} 모드)")
        
        # 시리얼 인터페이스 생성 (또는 기존 인터페이스 재사용)
        device_interface = self.get_or_create_interface(port, use_fake)
        
        # 장치 유형에 따라 적절한 컨트롤러 생성
        if "BELT" in device_id.upper():
            print(f"[DeviceManager] 벨트 컨트롤러 생성: {device_id}")
            return BeltController(device_interface, self.facility_status_manager)
        elif "GATE" in device_id.upper():
            print(f"[DeviceManager] 게이트 컨트롤러 생성: {device_id}")
            # 게이트 컨트롤러 생성 시 게이트 ID 전달
            controller = GateController(device_interface, self.facility_status_manager)
            controller.current_gate_id = device_id  # 현재 게이트 ID 설정
            return controller
        else:
            print(f"[DeviceManager ⚠️] 알 수 없는 장치 유형: {device_id}")
            return None
    
    # 지정된 장치의 컨트롤러 반환
    def get_controller(self, device_id: str) -> Optional[Any]:
        controller = self.controllers.get(device_id)
        if not controller:
            print(f"[DeviceManager ❌] {device_id} 장치가 등록되지 않았습니다. 등록된 장치: {list(self.controllers.keys())}")
        return controller

    # 모든 컨트롤러 종료
    def close_all(self):
        print(f"[DeviceManager] 모든 컨트롤러 종료 중...")
        
        for port, interface in self.interfaces.items():
            print(f"[DeviceManager] 인터페이스 종료: {port}")
            interface.close()
            
        for name, controller in self.controllers.items():
            print(f"[DeviceManager] {name} 컨트롤러 종료")
            
        print(f"[DeviceManager] 모든 컨트롤러 종료 완료")