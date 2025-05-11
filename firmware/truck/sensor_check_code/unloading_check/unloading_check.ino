#include <ESP32Servo.h>

Servo myServo;          // 서보 객체 생성
String inputString = ""; // 입력값 저장용 문자열

void setup() {
  Serial.begin(115200);
  myServo.attach(17);   // GPIO 17번에 서보모터 연결
  Serial.println("각도를 입력하세요 (0~180):");
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      int angle = inputString.toInt();  // 문자열을 정수로 변환
      if (angle >= 0 && angle <= 180) {
        myServo.write(angle);
        Serial.print("서보모터 이동: ");
        Serial.print(angle);
        Serial.println("도");
      } else {
        Serial.println("⚠️ 유효한 범위는 0~180도입니다.");
      }
      inputString = ""; // 입력 초기화
    } else {
      inputString += c; // 문자열 누적
    }
  }
}
