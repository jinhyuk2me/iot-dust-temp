#!/usr/bin/env python3
"""
간단한 벨트 테스트 도구 - 시리얼 통신을 통해 BELT_RUN 명령만 보냅니다.
"""

import serial
import time
import sys

# 포트 설정
PORT = "/dev/ttyACM0"  # 필요시 변경
BAUDRATE = 9600

try:
    # 시리얼 포트 연결
    print(f"[연결] 포트 {PORT}에 연결 중...")
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    time.sleep(2)  # 아두이노 리셋 대기
    
    # BELT_RUN 명령 전송
    command = "BELT_RUN\n"
    print(f"[전송] 명령: {command.strip()}")
    ser.write(command.encode())
    ser.flush()
    
    # 응답 읽기
    print("[응답 대기 중...]")
    for i in range(10):  # 최대 10번 응답 읽기
        if ser.in_waiting:
            response = ser.readline().decode().strip()
            print(f"[수신] 응답: {response}")
        time.sleep(0.5)
        
    # 연결 종료
    ser.close()
    print("[완료] 연결 종료")
    
except KeyboardInterrupt:
    print("\n[중단] 사용자에 의해 중단됨")
    if 'ser' in locals() and ser.is_open:
        ser.close()
        
except Exception as e:
    print(f"[오류] {e}")
    if 'ser' in locals() and ser.is_open:
        ser.close() 