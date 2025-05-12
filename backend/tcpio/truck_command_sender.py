from .protocol import TCPProtocol
import json

class TruckCommandSender:
    def __init__(self, truck_sockets: dict):
        self.truck_sockets = truck_sockets
    
    def send(self, truck_id: str, cmd: str, payload: dict = None) -> bool:
        if not self.is_registered(truck_id):
            print(f"[⚠️ 경고] {truck_id}가 등록되지 않음")
            return False

        try:
            # JSON 메시지 생성
            message = {
                "sender": "SERVER",
                "receiver": truck_id,
                "cmd": cmd,
                "payload": payload or {}
            }
            
            # 송신 메시지 로그 출력
            print(f"[📤 송신 원문] {json.dumps(message)}")
            
            # JSON 직렬화 및 전송
            self.truck_sockets[truck_id].sendall((json.dumps(message) + "\n").encode())
            print(f"[🚚 명령 전송] {truck_id} ← {cmd} | payload={payload}")
            return True
        except Exception as e:
            print(f"[❌ 전송 실패] {truck_id}: {e}")
            return False

    def is_registered(self, truck_id: str) -> bool:
        return truck_id in self.truck_sockets 