#include <ESP32Servo.h>

Servo myServo;  // 서보 객체 생성
int servoPin = 17;  // 서보 핀 설정

void setup() {
  Serial.begin(115200);         // 시리얼 통신 시작
  myServo.attach(servoPin);     // 서보 핀 연결
  Serial.println("서보 제어 시작 (0~180 입력)");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');  // 개행 기준으로 입력값 받기
    input.trim();  // 공백 제거

    if (input.length() > 0) {
      int angle = input.toInt();  // 문자열을 정수로 변환

      if (angle >= 0 && angle <= 180) {
        myServo.write(angle);  // 입력한 각도로 서보 회전
        Serial.print("서보 각도 설정: ");
        Serial.println(angle);
      } else {
        Serial.println("⚠️ 유효한 각도를 입력하세요 (0~180)");
      }
    }
  }
}
