# backend/serialio/serial_interface.py

import serial
import time
from backend.serialio.fake_serial import FakeSerial

class SerialInterface:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600, use_fake=False, debug=False):
        self.debug = debug
        if use_fake:
            self.ser = FakeSerial(name=port, debug=debug)
        else:
            self.ser = serial.Serial(port, baudrate, timeout=1)

    # ----------------------- 명령 전송 -----------------------

    # 구조화된 명령어 전송
    def send_command(self, target: str, action: str):
        command = self.build_command(target, action)
        print(f"[Serial Send] {command.strip()}")
        self.ser.write(command.encode())

    # 단순 텍스트 명령 전송
    def write(self, msg: str):
        try:
            self.ser.write((msg + '\n').encode())
        except Exception as e:
            print(f"[SerialInterface 오류] write 실패: {e}")

    # ----------------------- 프로토콜 파싱 -----------------------

    # 명령어 형식 생성
    @staticmethod
    def build_command(target: str, action: str) -> str:
        return f"{target.upper()}_{action.upper()}\n"
    
    # 응답 메시지 파싱
    @staticmethod
    def parse_response(response: str) -> dict:
        if not response:
            return {"type": "EMPTY", "raw": ""}
            
        response = response.strip()
        
        # 표준 응답 형식 처리 - ACK:COMMAND:RESULT
        if response.startswith("ACK:"):
            parts = response.split(":")
            if len(parts) >= 2:
                command = parts[1]
                # 결과가 없는 경우 빈 문자열로 처리
                result = parts[2] if len(parts) > 2 else ""
                return {
                    "type": "ACK",
                    "command": command,
                    "result": result,
                    "raw": response
                }
                
        # 상태 응답 처리 - STATUS:TARGET:STATE
        elif response.startswith("STATUS:"):
            parts = response.split(":")
            if len(parts) >= 3:
                return {
                    "type": "STATUS",
                    "target": parts[1],
                    "state": parts[2],
                    "raw": response
                }
                
        # 게이트 응답 처리 (하위 호환성)
        elif "GATE_" in response:
            if "_OPENED" in response:
                gate_id = response.split("_")[0]
                return {
                    "type": "GATE",
                    "gate_id": gate_id,
                    "state": "OPENED",
                    "raw": response
                }
            elif "_CLOSED" in response:
                gate_id = response.split("_")[0]
                return {
                    "type": "GATE",
                    "gate_id": gate_id,
                    "state": "CLOSED",
                    "raw": response
                }
                
        # 벨트 응답 처리 (하위 호환성)
        elif "BELT" in response:
            if "STARTED" in response or "RUNNING" in response:
                return {
                    "type": "BELT",
                    "state": "RUNNING",
                    "raw": response
                }
            elif "STOPPED" in response:
                return {
                    "type": "BELT",
                    "state": "STOPPED",
                    "raw": response
                }
            elif "EMERGENCY_STOP" in response:
                return {
                    "type": "BELT",
                    "state": "EMERGENCY_STOP",
                    "raw": response
                }
                
        # 이모지 응답 처리
        elif "🔓" in response or "🔒" in response:
            gate_letter = None
            for char in response:
                if char in "ABC":
                    gate_letter = char
                    break
                    
            if gate_letter:
                state = "OPENED" if "🔓" in response else "CLOSED"
                return {
                    "type": "GATE",
                    "gate_id": f"GATE_{gate_letter}",
                    "state": state
                }
                
        # 한글 응답 처리
        elif "게이트" in response:
            gate_letter = None
            for char in response:
                if char in "ABC":
                    gate_letter = char
                    break
                    
            if gate_letter:
                state = "OPENED" if "열림" in response else "CLOSED"
                return {
                    "type": "GATE",
                    "gate_id": f"GATE_{gate_letter}",
                    "state": state
                }
                
        # 컨테이너 상태 처리
        elif response == "ConA_FULL":
            return {
                "type": "CONTAINER",
                "state": "FULL"
            }
            
        # 알 수 없는 응답
        return {
            "type": "UNKNOWN",
            "raw": response
        }

    # ----------------------- 응답 수신 -----------------------

    # 응답 수신
    def read_response(self, timeout=5):
        start_time = time.time()
        wait_count = 0
        
        print(f"[SerialInterface] 응답 대기 시작 (최대 {timeout}초)")
        
        while time.time() - start_time < timeout:
            # 주기적으로 대기 중임을 표시
            if wait_count % 20 == 0:  # 2초마다 로그
                print(f"[SerialInterface] 응답 대기 중... (경과: {time.time() - start_time:.1f}초)")
            wait_count += 1
            
            if self.ser.in_waiting:
                try:
                    # 반복문으로 여러 줄이 왔을 때 처리 가능하도록
                    line = self.ser.readline().decode().strip()
                    if not line:
                        time.sleep(0.1)
                        continue
                    
                    # 응답 파싱
                    parsed = self.parse_response(line)
                    
                    # 응답 타입에 따른 로깅
                    if parsed["type"] == "ACK":
                        command = parsed.get("command", "")
                        result = parsed.get("result", "")
                        print(f"[✅ 명령 응답] {command}: {result}")
                    elif parsed["type"] == "STATUS":
                        target = parsed.get("target", "")
                        state = parsed.get("state", "")
                        print(f"[📊 상태 알림] {target}: {state}")
                    elif parsed["type"] == "GATE":
                        gate_id = parsed.get("gate_id", "")
                        state = parsed.get("state", "")
                        print(f"[🚪 게이트 {gate_id} 상태] {state}")
                    elif parsed["type"] == "BELT":
                        print(f"[🔄 벨트 상태] {parsed['state']}")
                    elif parsed["type"] == "CONTAINER":
                        print(f"[📦 컨테이너 상태] {parsed['state']}")
                    else:
                        print(f"[ℹ️ 기타 응답] {line}")
                        
                    return line
                    
                except Exception as e:
                    print(f"[SerialInterface 오류] 응답 읽기 실패: {e}")
                    time.sleep(0.1)
                    continue
                    
            time.sleep(0.1)
            
        print(f"[SerialInterface ⚠️] 응답 시간 초과 ({timeout}초)")
        return None

    # 시리얼 연결 종료
    def close(self):
        if self.ser:
            self.ser.close()
            print(f"[SerialInterface] 연결 종료") 