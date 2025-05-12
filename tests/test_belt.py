#!/usr/bin/env python3
"""
벨트 테스트 도구 - 시리얼 통신을 통해 BELT_RUN 명령을 보내고 응답을 확인합니다.
"""

import serial
import time
import argparse
import sys

class BeltTester:
    def __init__(self, port, baudrate=9600):
        """벨트 테스터 초기화"""
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        
    def connect(self):
        """시리얼 포트에 연결"""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"✅ 포트 {self.port}에 연결됨 (속도: {self.baudrate})")
            return True
        except Exception as e:
            print(f"❌ 연결 실패: {e}")
            return False
            
    def send_belt_run(self):
        """BELT_RUN 명령 전송"""
        if not self.serial:
            print("❌ 연결되지 않음. connect() 먼저 호출하세요.")
            return
            
        try:
            cmd = "BELT_RUN\n"
            print(f"➡️ 전송: {cmd.strip()}")
            self.serial.write(cmd.encode())
            self.serial.flush()
            
            # 응답 대기
            time.sleep(0.5)
            response = self.read_response()
            
            return response
        except Exception as e:
            print(f"❌ 명령 전송 실패: {e}")
            return None
            
    def read_response(self, timeout=5):
        """응답 읽기"""
        responses = []
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            if self.serial.in_waiting:
                try:
                    line = self.serial.readline().decode().strip()
                    if line:
                        print(f"⬅️ 수신: {line}")
                        responses.append(line)
                except Exception as e:
                    print(f"❌ 응답 읽기 실패: {e}")
            
            # 더 이상 들어오는 데이터가 없으면 종료
            if not self.serial.in_waiting and responses:
                break
                
            time.sleep(0.1)
            
        return responses
            
    def close(self):
        """연결 종료"""
        if self.serial:
            self.serial.close()
            print(f"✅ 포트 {self.port} 연결 종료")
            

def main():
    parser = argparse.ArgumentParser(description="벨트 테스트 도구")
    parser.add_argument("-p", "--port", default="/dev/ttyACM0", help="시리얼 포트 (기본값: /dev/ttyACM0)")
    parser.add_argument("-b", "--baudrate", type=int, default=9600, help="통신 속도 (기본값: 9600)")
    parser.add_argument("-c", "--count", type=int, default=1, help="명령 전송 횟수 (기본값: 1)")
    parser.add_argument("-i", "--interval", type=float, default=3, help="명령 사이 간격(초) (기본값: 3)")
    
    args = parser.parse_args()
    
    tester = BeltTester(args.port, args.baudrate)
    
    if not tester.connect():
        sys.exit(1)
        
    try:
        # 명령 여러 번 보내기
        for i in range(args.count):
            if i > 0:
                print(f"⏳ {args.interval}초 대기 중...")
                time.sleep(args.interval)
                
            print(f"\n📨 명령 {i+1}/{args.count} 전송")
            response = tester.send_belt_run()
            
            if response:
                print(f"✅ 응답 수신: {response}")
            else:
                print("❌ 응답 없음")
                
        print("\n✅ 테스트 완료")
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
    finally:
        tester.close()


if __name__ == "__main__":
    main() 