#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>
#include <Arduino.h>

/*---------- RFID ----------*/
#define SS_PIN 21
#define RST_PIN 22
MFRC522 rfid(SS_PIN, RST_PIN);

struct UIDEntry {
  byte uid[4];
  const char* description;
};

UIDEntry registeredCards[] = {
  { {0x86, 0x51, 0x0A, 0x05}, "CHECKPOINT_A" },
  { {0x12, 0x6D, 0x07, 0x05}, "CHECKPOINT_B" },
  { {0xD9, 0x3F, 0x09, 0x05}, "load_A" },
  { {0xA3, 0x8F, 0x09, 0x05}, "load_B" },
  { {0x9C, 0x84, 0x0B, 0x05}, "CHECKPOINT_C" },
  { {0x83, 0x58, 0xAE, 0x1A}, "BELT" },
  { {0x63, 0x9D, 0x9F, 0x35}, "CHECKPOINT_D" },
  { {0xF3, 0x16, 0x63, 0x1B}, "STANDBY" },
};
const int numRegistered = sizeof(registeredCards) / sizeof(registeredCards[0]);

/*---------- 라인트레이서 ----------*/
#define LEFT_SENSOR 34
#define RIGHT_SENSOR 35

double Kp = 0.1024, Ki = 0.0001, Kd = 0.2;
double PID_control, integral = 0.0;
int error, last_error = 0, derivative;
int avg_PWM = 150, max_pwm = 75;
int L_PWM, R_PWM;
int l_sensor_val, r_sensor_val;

bool standby_mode = false;
bool is_turning = false;
bool wait_for_line = false;
unsigned long turn_start_time = 0;

/*---------- 모터 ----------*/
#define MOTOR12_EN 27
#define MOTOR34_EN 13
#define MOTOR1_IN1 26
#define MOTOR1_IN2 25
#define MOTOR2_IN3 12
#define MOTOR2_IN4 14
#define PWM_CHANNEL_LEFT 0
#define PWM_CHANNEL_RIGHT 1
#define PWM_FREQ 1000
#define PWM_RESOLUTION 8

/*---------- 초음파 ----------*/
#define TRIG_PIN 33
#define ECHO_PIN 32
float last_distance_cm = 0;

/*---------- 배터리 ----------*/
int battery_level = 100;
unsigned long last_battery_drop = 0;
const unsigned long BATTERY_DROP_INTERVAL = 5000;
bool battery_empty = false;

void setup() {
  Serial.begin(115200);

  pinMode(MOTOR1_IN1, OUTPUT); pinMode(MOTOR1_IN2, OUTPUT);
  pinMode(MOTOR2_IN3, OUTPUT); pinMode(MOTOR2_IN4, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT); pinMode(ECHO_PIN, INPUT);

  ledcSetup(PWM_CHANNEL_LEFT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(MOTOR12_EN, PWM_CHANNEL_LEFT);
  ledcSetup(PWM_CHANNEL_RIGHT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(MOTOR34_EN, PWM_CHANNEL_RIGHT);

  SPI.begin(18, 19, 23, 21);
  rfid.PCD_Init();
  Serial.println("✅ RFID 리더 초기화 완료");
}

void loop() {
  unsigned long current_time = millis();

  if (battery_level <= 30 && !is_turning && !standby_mode) {
    Serial.println("⚠️ 배터리 부족 → 회전 시작");
    start_turn();
    standby_mode = true;
  }

  handle_turn();

  if (!battery_empty && !is_turning && !obstacle_detected()) {
    line_trace();
  } else if (!is_turning) {
    stop_motors();
  }

  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    checkAndPrintUID(rfid.uid.uidByte);
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
  }

  if (current_time - last_battery_drop >= BATTERY_DROP_INTERVAL) {
    last_battery_drop = current_time;
    battery_level -= 10;
    Serial.print("🪫 배터리 잔량: "); Serial.print(battery_level); Serial.println("%");

    if (battery_level <= 0) {
      battery_level = 0;
      battery_empty = true;
      stop_motors();
      Serial.println("❌ 배터리 0% → 정지");
    }
  }
}

void start_turn() {
  digitalWrite(MOTOR1_IN1, LOW);
  digitalWrite(MOTOR1_IN2, HIGH);
  digitalWrite(MOTOR2_IN3, HIGH);
  digitalWrite(MOTOR2_IN4, LOW);
  ledcWrite(PWM_CHANNEL_LEFT, 80);
  ledcWrite(PWM_CHANNEL_RIGHT, 80);

  turn_start_time = millis();
  is_turning = true;
  wait_for_line = false;
}

void handle_turn() {
  if (!is_turning) return;

  unsigned long now = millis();

  if (!wait_for_line && now - turn_start_time >= 500) {
    wait_for_line = true;
    Serial.println("🕵️‍♂️ 라인 탐색 시작");
  }

  if (wait_for_line) {
    int left = analogRead(LEFT_SENSOR);
    int right = analogRead(RIGHT_SENSOR);
    if (left < 500 || right < 500) {
      Serial.println("✅ 라인 감지됨 → 회전 종료");
      stop_motors();
      is_turning = false;
      wait_for_line = false;
    } else {
      digitalWrite(MOTOR1_IN1, LOW);
      digitalWrite(MOTOR1_IN2, HIGH);
      digitalWrite(MOTOR2_IN3, HIGH);
      digitalWrite(MOTOR2_IN4, LOW);
      ledcWrite(PWM_CHANNEL_LEFT, 80);
      ledcWrite(PWM_CHANNEL_RIGHT, 80);
    }
  }
}

void line_trace() {
  l_sensor_val = analogRead(LEFT_SENSOR);
  r_sensor_val = analogRead(RIGHT_SENSOR);
  error = l_sensor_val - r_sensor_val;
  integral += error;
  derivative = error - last_error;
  PID_control = Kp * error + Ki * integral + Kd * derivative;
  last_error = error;

  L_PWM = constrain(avg_PWM + PID_control, 0, max_pwm);
  R_PWM = constrain(avg_PWM - PID_control, 0, max_pwm);

  left_motor_f(L_PWM);
  right_motor_f(R_PWM);
}

void left_motor_f(int pwm_val) {
  digitalWrite(MOTOR1_IN1, LOW);
  digitalWrite(MOTOR1_IN2, HIGH);
  ledcWrite(PWM_CHANNEL_LEFT, pwm_val);
}

void right_motor_f(int pwm_val) {
  digitalWrite(MOTOR2_IN3, LOW);
  digitalWrite(MOTOR2_IN4, HIGH);
  ledcWrite(PWM_CHANNEL_RIGHT, pwm_val);
}

void stop_motors() {
  ledcWrite(PWM_CHANNEL_LEFT, 0);
  ledcWrite(PWM_CHANNEL_RIGHT, 0);
}

bool obstacle_detected() {
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH);
  if (duration == 0) return false;
  last_distance_cm = duration * 0.034 / 2.0;
  return last_distance_cm < 12.0;
}

bool isSameUID(byte *uid1, byte *uid2) {
  for (byte i = 0; i < 4; i++) {
    if (uid1[i] != uid2[i]) return false;
  }
  return true;
}

void checkAndPrintUID(byte* uid) {
  for (int i = 0; i < numRegistered; i++) {
    if (isSameUID(uid, registeredCards[i].uid)) {
      Serial.print("✅ 등록된 태그: ");
      Serial.println(registeredCards[i].description);
      if (strcmp(registeredCards[i].description, "STANDBY") == 0) {
        Serial.println("🔋 STANDBY 도착 → 배터리 충전됨");
        battery_level = 100;
        battery_empty = false;
        stop_motors();
      }
      return;
    }
  }
  Serial.println("❌ 등록되지 않은 태그");
}

