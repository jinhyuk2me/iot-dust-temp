# backend/serialio/fake_serial.py

import threading
import time
import re

class FakeSerial:
    # 클래스 레벨 변수로 마지막으로 사용된 게이트 ID 추적
    last_gate_id = "GATE_A"
    
    def __init__(self, name="TRUCK_01", poll_interval=0.1, debug=False):
        self.name = name
        self.buffer = []
        self.in_waiting = 0
        self.lock = threading.Lock()
        self.poll_interval = poll_interval
        self.running = True
        self.debug = debug
        self.polling_thread = threading.Thread(target=self._polling_loop)
        self.polling_thread.daemon = True  # 메인 스레드 종료 시 자동 종료
        self.polling_thread.start()
        if self.debug:
            print(f"[FakeSerial] {name} 인스턴스 생성됨")

    def _polling_loop(self):
        while self.running:
            self.readline()  # 주기적으로 readline 호출
            time.sleep(self.poll_interval)

    def write(self, data: bytes):
        msg = data.decode().strip()
        if self.debug:
            print(f"[FakeSerial:{self.name}] 받은 명령: {msg}")
        
        # 게이트 ID 업데이트 (명령에서 게이트 ID 추출)
        gate_pattern = re.compile(r'(GATE_[ABC])_(\w+)', re.IGNORECASE)
        gate_match = gate_pattern.match(msg)
        if gate_match:
            FakeSerial.last_gate_id = gate_match.group(1).upper()
            if self.debug:
                print(f"[FakeSerial:{self.name}] 마지막 게이트 ID 업데이트: {FakeSerial.last_gate_id}")

        response = self._simulate_response(msg)
        if response:
            with self.lock:
                self.buffer.append((response + "\n").encode())
                self.in_waiting = len(self.buffer)
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 즉시 응답 추가: {response}")

    def readline(self):
        with self.lock:
            if self.buffer:
                response = self.buffer.pop(0)
                self.in_waiting = len(self.buffer)
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 응답 읽기: {response.decode().strip()}")
                return response
            else:
                # 버퍼가 비어있음을 로그로 기록
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 버퍼가 비어있음 - 빈 응답 반환")
                return b""

    def _simulate_response(self, msg: str):
        # ✅ 게이트 명령 시뮬레이션 - 정규식으로 더 유연하게 처리
        gate_pattern = re.compile(r'(GATE_[ABC])_(\w+)', re.IGNORECASE)
        gate_match = gate_pattern.match(msg)
        
        if gate_match:
            gate_id = gate_match.group(1).upper()
            action = gate_match.group(2).upper()
            
            if self.debug:
                print(f"[FakeSerial:{self.name}] 게이트 명령 감지: {gate_id}_{action}")
            
            if action == "OPEN":
                # 게이트 열림 지연 (0.5초로 단축)
                if self.debug:
                    print(f"[FakeSerial:{self.name}] {gate_id} 열림 작업 시작 (0.5초 소요)")
                # 표준 프로토콜 형식 사용
                # ACK:COMMAND:RESULT 형식
                self._schedule_delayed_response(0.5, f"ACK:{gate_id}_OPEN:SUCCESS")
                # 상태 메시지도 전송
                self._schedule_delayed_response(0.6, f"STATUS:{gate_id}:OPENED")
                return None  # 즉시 응답 없음, 지연 후 응답이 전송됨
            elif action == "CLOSE":
                # 게이트 닫힘 지연 (0.5초로 단축)
                if self.debug:
                    print(f"[FakeSerial:{self.name}] {gate_id} 닫힘 작업 시작 (0.5초 소요)")
                # 표준 프로토콜 형식 사용
                # ACK:COMMAND:RESULT 형식
                self._schedule_delayed_response(0.5, f"ACK:{gate_id}_CLOSE:SUCCESS")
                # 상태 메시지도 전송
                self._schedule_delayed_response(0.6, f"STATUS:{gate_id}:CLOSED")
                return None  # 즉시 응답 없음, 지연 후 응답이 전송됨
        
        # 직접 "OPEN" 명령도 처리
        elif msg == "OPEN":
            # 현재 제어 중인 게이트 ID 결정 (포트 이름에서 추출)
            gate_id = self._extract_gate_id_from_name()
            
            if self.debug:
                print(f"[FakeSerial:{self.name}] 직접 OPEN 명령 감지 - 게이트 ID: {gate_id}")
            
            # 표준 프로토콜 형식 사용
            # ACK:COMMAND:RESULT 형식
            self._schedule_delayed_response(0.5, f"ACK:{gate_id}_OPEN:SUCCESS")
            # 상태 메시지도 전송
            self._schedule_delayed_response(0.6, f"STATUS:{gate_id}:OPENED")
            return None  # 즉시 응답 없음, 지연 후 응답이 전송됨
            
        # 직접 "CLOSE" 명령도 처리
        elif msg == "CLOSE":
            # 현재 제어 중인 게이트 ID 결정 (포트 이름에서 추출)
            gate_id = self._extract_gate_id_from_name()
            
            if self.debug:
                print(f"[FakeSerial:{self.name}] 직접 CLOSE 명령 감지 - 게이트 ID: {gate_id}")
            
            # 표준 프로토콜 형식 사용
            # ACK:COMMAND:RESULT 형식
            self._schedule_delayed_response(0.5, f"ACK:{gate_id}_CLOSE:SUCCESS")
            # 상태 메시지도 전송
            self._schedule_delayed_response(0.6, f"STATUS:{gate_id}:CLOSED")
            return None  # 즉시 응답 없음, 지연 후 응답이 전송됨

        # ✅ 벨트 명령 시뮬레이션
        elif msg == "BELT_RUN":
            if self.debug:
                print(f"[FakeSerial:{self.name}] 벨트 작동 명령 감지")
            # 표준 프로토콜 형식 사용
            # ACK:COMMAND:RESULT 형식
            immediate_response = "ACK:BELT_RUN:SUCCESS"
            # 상태 메시지도 스케줄링
            self._schedule_delayed_response(0.1, "STATUS:BELT:RUNNING")
            self._schedule_delayed_response(20, "STATUS:BELT:STOPPED")
            return immediate_response
            
        elif msg == "BELT_STOP" or msg == "BELTOFF":
            if self.debug:
                print(f"[FakeSerial:{self.name}] 벨트 정지 명령 감지")
            # 표준 프로토콜 형식 사용
            # ACK:COMMAND:RESULT 형식
            return "ACK:BELT_STOP:SUCCESS"
            
        elif msg == "BELT_EMRSTOP" or msg == "EMRSTOP":
            if self.debug:
                print(f"[FakeSerial:{self.name}] 벨트 비상정지 명령 감지")
            # 표준 프로토콜 형식 사용
            # ACK:COMMAND:RESULT 형식
            return "ACK:BELT_EMRSTOP:SUCCESS"
            
        else:
            if self.debug:
                print(f"[FakeSerial:{self.name}] 알 수 없는 명령: {msg}")

        return None
    
    def _extract_gate_id_from_name(self):
        """
        포트 이름/장치 이름에서 게이트 ID를 추출합니다.
        """
        # 포트 이름에 "GATE_"가 있는 경우
        if "GATE_" in self.name:
            return self.name
        
        # 마지막으로 사용된 게이트 ID 사용
        if FakeSerial.last_gate_id:
            return FakeSerial.last_gate_id
            
        # 포트 이름에 "GATE_"가 없지만 특별한 패턴이 있는 경우
        # 예: /dev/ttyACM1 -> GATE_A, GATE_B 중 하나로 결정
        match = re.search(r'ttyACM(\d+)', self.name)
        if match:
            port_num = int(match.group(1))
            if port_num == 1:  # 예: 여러 게이트가 포트를 공유하는 경우
                return "GATE_A"  # 기본값으로 GATE_A 반환
            else:
                return "BELT"  # 다른 포트는 벨트로 가정
        
        # 기본적으로 GATE_A 반환
        return "GATE_A"

    def _schedule_delayed_response(self, delay_seconds, response):
        """
        지연된 응답 전송을 스케줄링합니다.
        
        Args:
            delay_seconds: 지연 시간(초)
            response: 응답 문자열
        """
        if self.debug:
            print(f"[FakeSerial:{self.name}] {delay_seconds}초 후 응답 예약: {response}")
        
        # 스레드 시작 전 running 상태 확인
        if self.running:
            thread = threading.Timer(delay_seconds, self._enqueue_response, args=[response])
            thread.daemon = True  # 메인 스레드 종료 시 자동 종료
            thread.start()

    def _enqueue_response(self, response):
        """
        응답 큐에 메시지를 추가합니다.
        
        Args:
            response: 응답 문자열
        """
        # running 상태 확인
        if not self.running:
            return
            
        with self.lock:
            self.buffer.append((response + "\n").encode())
            self.in_waiting = len(self.buffer)
            if self.debug:
                print(f"[FakeSerial:{self.name}] 응답 큐에 추가됨: {response} (큐 크기: {len(self.buffer)})")

    def close(self):
        """시리얼 연결을 종료합니다."""
        self.running = False
        if hasattr(self, 'polling_thread') and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=1.0)  # 최대 1초 대기
        if self.debug:
            print(f"[FakeSerial:{self.name}] 연결 종료")
