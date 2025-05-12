#include <Servo.h>

const int MOTOR_PIN_A = 5;  // PWM
const int MOTOR_PIN_B = 6;  // PWM
const int SERVO_PIN = 9;    // 서보는 Servo.write() 사용
const int SENSOR_PIN_A = A0;
const int SENSOR_PIN_B = A1;
const int CDS_THRESHOLD = 600;  // 조도센서 기준값

const int MOTOR_SPEED = 100; // PWM 속도

// enum 대체: ROUTE_A = 0, ROUTE_B = 1, ROUTE_NONE = 2
#define ROUTE_A 0
#define ROUTE_B 1
#define ROUTE_NONE 2
int currentRoute = ROUTE_A;
int routeLock = ROUTE_NONE;

unsigned long motorStartTime = 0;
unsigned long motorEndTime = 0;  // [추가] 종료시각 저장
unsigned long remainingTime = 0;
const unsigned long MOTOR_DURATION = 20000; // 20초
bool motorRunning = false;

Servo conveyorServo;

void setup() {
  pinMode(MOTOR_PIN_A, OUTPUT);
  pinMode(MOTOR_PIN_B, OUTPUT);
  Serial.begin(9600);
  conveyorServo.attach(SERVO_PIN);
  conveyorServo.write(50);
  Serial.println("STATUS:BELT:ROUTE_A"); // default A route
}

void loop() {
  reportStatus() ;
  if (Serial.available() > 0) {
  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "BELT_RUN" && !motorRunning) {
    if (decideRoute()) {
      startMotor(MOTOR_DURATION);
      Serial.println("ACK:BELT_RUN:OK");
    } else {
      Serial.println("ACK:BELT_RUN:FAIL");
    }
  } 
  else if (command == "BELT_STOP") {
    stopMotor();
    Serial.println("ACK:BELT_STOP:OK");
  }
}

  if (motorRunning) {
    if (millis() >= motorEndTime) {  // [수정] motorEndTime 기준으로 종료 판단
      stopMotor();
    }

    if (isWarehouseFull(currentRoute)) {
      unsigned long elapsed = millis() - motorStartTime;
      stopMotor();
      remainingTime = motorEndTime - millis();  // [수정] 정확한 남은 시간 계산

      if (currentRoute == ROUTE_A && !isWarehouseFull(ROUTE_B)) {
        currentRoute = ROUTE_B;
        routeLock = ROUTE_B;
        conveyorServo.write(130);
        Serial.println("STATUS:BELT:ROUTE_B");
      } else if (currentRoute == ROUTE_B && !isWarehouseFull(ROUTE_A)) {
        currentRoute = ROUTE_A;
        routeLock = ROUTE_A;
        conveyorServo.write(50);
        Serial.println("STATUS:BELT:ROUTE_A");
      } else {
        Serial.println("STATUS:SYSTEM:ALL_FULL:RUNTIME");
        return;
      }

      delay(1000); // 서보 회전 대기(이미 구동한시간저장해둠 딜레이OK)
      startMotor(remainingTime);  // 남은 시간으로 재시작
      Serial.print("STATUS:BELT:REMAINING_TIME:");
      Serial.println(remainingTime);
    }
  }
}

//초기 구동 방향성 제시
bool decideRoute() {
  if (routeLock != ROUTE_NONE) {
    currentRoute = routeLock;
    return true;
  }

  bool fullA = isWarehouseFull(ROUTE_A);
  bool fullB = isWarehouseFull(ROUTE_B);

  if (!fullA) {
    currentRoute = ROUTE_A;
    routeLock = ROUTE_A;
  } 
  else if (!fullB) {
    currentRoute = ROUTE_B;
    routeLock = ROUTE_B;
  } 
  else {
    Serial.println("STATUS:SYSTEM:ALL_FULL:INITIALIZATION");
    return false;
  }

  if (currentRoute == ROUTE_A) {
    conveyorServo.write(50);
    Serial.println("STATUS:BELT:ROUTE_A");
   
  } 
  else if (currentRoute == ROUTE_B) {
    conveyorServo.write(130);
    Serial.println("STATUS:BELT:ROUTE_B");
    delay(800);
  }

  return true;
}

// [수정] duration 인자를 받도록 수정
void startMotor(unsigned long duration) {
  analogWrite(MOTOR_PIN_A, MOTOR_SPEED);
  analogWrite(MOTOR_PIN_B, 0);
  motorStartTime = millis();
  motorEndTime = motorStartTime + duration;
  motorRunning = true;
  Serial.print("STATUS:BELT:DURATION:");
  Serial.println(duration);
  Serial.println("STATUS:BELT:RUNNING");
}

void stopMotor() {
  analogWrite(MOTOR_PIN_A, 0);
  analogWrite(MOTOR_PIN_B, 0);
  motorRunning = false;
  Serial.println("STATUS:BELT:STOPPED");
}

bool isWarehouseFull(int route) {
  int value = 0;
  if (route == ROUTE_A) {
    value = analogRead(SENSOR_PIN_A);
  } else if (route == ROUTE_B) {
    value = analogRead(SENSOR_PIN_B);
  }
  return value < CDS_THRESHOLD;
}

int lastAState = -1;
int lastBState = -1;

void reportStatus() {
  int aNow = isWarehouseFull(ROUTE_A);
  int bNow = isWarehouseFull(ROUTE_B);

  if (aNow != lastAState || bNow != lastBState) {
    Serial.print("STATUS:CONTAINER_A:");
    Serial.println(aNow ? "FULL" : "EMPTY");
    Serial.print("STATUS:CONTAINER_B:");
    Serial.println(bNow ? "FULL" : "EMPTY");

    lastAState = aNow;
    lastBState = bNow;
  }
}