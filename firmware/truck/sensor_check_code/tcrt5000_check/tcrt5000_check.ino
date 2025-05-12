const int sensorPin1 = 34;   // TCRT5000 센서 1번 핀 (D34)  왼쪽
const int sensorPin2 = 35;   // TCRT5000 센서 2번 핀 (D35)  오른쪽
const int ledPin = 2;        // 상태 확인용 LED (내장 LED는 보통 GPIO 2)

void setup() {
  pinMode(ledPin, OUTPUT);
  Serial.begin(115200);      // ESP는 속도 115200이 일반적
}

void loop() {
  int value1 = analogRead(sensorPin1);  // 센서 1값 읽기
  int value2 = analogRead(sensorPin2);  // 센서 2값 읽기

  Serial.print("Sensor1: ");
  Serial.print(value1);
  Serial.print("  |  Sensor2: ");
  Serial.println(value2);

  // 둘 중 하나라도 어두운 라인을 감지하면 LED ON
  if (value1 < 500 || value2 < 500) {
    digitalWrite(ledPin, HIGH);
  } else {
    digitalWrite(ledPin, LOW);
  }

  //delay(100);
}