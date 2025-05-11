import threading
import time
from typing import Optional

class SerialController:
    def __init__(self, serial_interface):
        self.interface = serial_interface
        self.running = True
        self.polling_thread: Optional[threading.Thread] = None
    
    # 시리얼 폴링 시작  
    def start_polling(self):
        if self.polling_thread and self.polling_thread.is_alive():
            print(f"[{self.__class__.__name__}] 이미 폴링 중")
            return False  # 이미 실행 중
            
        self.polling_thread = threading.Thread(
            target=self.poll_serial,
            daemon=True
        )
        self.running = True
        self.polling_thread.start()
        print(f"[{self.__class__.__name__}] 시리얼 폴링 시작")
        return True
        
    # 시리얼 폴링 중지
    def stop_polling(self):
        if not self.polling_thread or not self.polling_thread.is_alive():
            return False
            
        self.running = False
        self.polling_thread.join(timeout=1)
        print(f"[{self.__class__.__name__}] 시리얼 폴링 중지")
        return True
        
    # 시리얼 폴링 루프
    def poll_serial(self):
        device_name = self.__class__.__name__
        print(f"[{device_name}] 시리얼 폴링 시작")
        try:
            while self.running:
                try:
                    line = self.interface.read_response(timeout=1)  # 짧은 타임아웃
                    if line and isinstance(line, str):
                        self.handle_message(line)
                except Exception as e:
                    print(f"[{device_name} 경고] 폴링 중 오류: {e}")
                    # 일시적 오류시 중단 방지
                time.sleep(0.01)  # CPU 사용량 감소
        except Exception as e:
            print(f"[{device_name} 오류] 시리얼 폴링 중단: {e}")
        finally:
            print(f"[{device_name}] 시리얼 폴링 종료")
    
    # 메시지 처리
    def handle_message(self, message: str):
        raise NotImplementedError("자식 클래스에서 구현해야 합니다")
    
    # 응답 읽기
    def read_response(self, timeout=5):
        return self.interface.read_response(timeout=timeout)
    
    # 명령 전송
    def send_command(self, target: str, action: str):
        """
        표준화된 형식으로 명령 전송
        
        Args:
            target: 대상 (예: "GATE_A", "BELT")
            action: 동작 (예: "OPEN", "CLOSE", "RUN", "STOP")
            
        Returns:
            bool: 성공 여부
        """
        try:
            self.interface.send_command(target, action)
            return True
        except Exception as e:
            print(f"[{self.__class__.__name__}] 명령 전송 오류: {e}")
            return False
    
    # 직접 쓰기
    def write(self, message: str):
        """
        직접 메시지 쓰기
        
        Args:
            message: 전송할 메시지
            
        Returns:
            bool: 성공 여부
        """
        try:
            self.interface.write(message)
            return True
        except Exception as e:
            print(f"[{self.__class__.__name__}] 메시지 쓰기 오류: {e}")
            return False
        
    # 종료
    def close(self):
        self.running = False
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=1)
        if hasattr(self.interface, 'close'):
            self.interface.close()
        print(f"[{self.__class__.__name__}] 종료됨") 