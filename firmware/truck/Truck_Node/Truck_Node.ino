#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <ESP32Servo.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include <time.h>

/*--------------------------------WiFi 설정--------------------------------*/

const char* ssid = "addinedu_class_2 (2.4G)";
const char* password = "addinedu1";

/*--------------------------------PC 서버 주소 및 포트--------------------------------*/

IPAddress serverIP(192, 168, 0, 166);  // ← PC IP로 바꾸세요
const int serverPort = 8001;  
WiFiClient client;
String incoming_msg = "";

/*--------------------------------등록된 UID 목록--------------------------------*/

struct UIDEntry 
{
  byte uid[4];
  const char* description;
};

UIDEntry registeredCards[] = {
  // { {0x8B, 0xEE, 0xC9, 0x01}, "CHARGE_LOCATION" },
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

unsigned long last_rfid_check = 0;
const unsigned long RFID_CHECK_INTERVAL = 300;  // 0.3초마다 RFID 체크

/*--------------------------------트럭 ID 설정--------------------------------*/

char* truck_id = "TRUCK_01";

/*-------------------------상태 로직 변환 및 기타 변수들--------------------------------*/

bool run_command = false;
bool obstacle_block = false;   //지금 멈춰야 하나?(실시간 결정용)
bool prev_obstacle_state = false;
float last_distance_cm = 0;

String current_position = "UNKNOWN";
String last_cmd = "";
String mission_target = "";
unsigned long last_mission_check = 0;    // 마지막 미션 체크 시간
const unsigned long MISSION_CHECK_INTERVAL = 5000;  // 5초마다 체크

/*-------------------------loading 변수들--------------------------------*/

bool wait_start_loading = false;
unsigned long wait_start_loading_time = 0;

bool loading_in_progress = false;
unsigned long loading_start_time = 0;

/*-------------------------unloading 변수들--------------------------------*/
bool wait_start_unloading = false;
unsigned long wait_start_unloading_time = 0;

bool unloading_in_progress = false;
unsigned long unloading_start_time = 0;

unsigned long unloading_stage_time = 0;
int unloading_stage = 0;

// 서보모터 제어 관련 전역 변수
Servo unloading_servo;
const int SERVO_PIN = 17;
const int SERVO_INIT_ANGLE = 170;
const int SERVO_DROP_ANGLE = 90;
bool unloading_servo_moved = false;  // 서보 동작 완료 체크

/*--------------------------------가상 배터리 잔량 체크--------------------------------*/

int battery_level = 100;

unsigned long last_battery_drop = 0;
const unsigned long BATTERY_DROP_INTERVAL = 5000; //5초 마다 배터리 감소 

unsigned long last_battery_report = 0;
const unsigned long BATTERY_REPORT_INTERVAL = 5000; // 5초마다 배터리 상태 서버에 전송
bool battery_empty = false;  // 배터리 0% 상태 플래그


/*--------------------------------모터 제어 핀 및 PWM--------------------------------*/

#define MOTOR12_EN 27    // PWM 채널 0
#define MOTOR34_EN 13    // PWM 채널 1
#define MOTOR1_IN1 26
#define MOTOR1_IN2 25
#define MOTOR2_IN3 12
#define MOTOR2_IN4 14

#define PWM_FREQ 1000
#define PWM_RESOLUTION 8
#define PWM_CHANNEL_LEFT 0
#define PWM_CHANNEL_RIGHT 1

/*--------------------------------초음파 센서 핀--------------------------------*/

#define TRIG_PIN 33
#define ECHO_PIN 32

/*--------------------------------rfid 센서 핀--------------------------------*/

#define SS_PIN 21    // SDA
#define RST_PIN 22   // RST

/*--------------------------------적외선 센서 핀--------------------------------*/
#define LEFT_SENSOR 34
#define RIGHT_SENSOR 35

/*--------------------------------PID 제어 변수--------------------------------*/

double Kp = 0.1020;
double Kd = 0.2;
double Ki = 0.0001;       
double integral = 0.0;  // 누적 적분값
double PID_control;
int last_error = 0;
int derivative;
int L_PWM, R_PWM;
int error;
int l_sensor_val;
int r_sensor_val;
int avg_PWM = 150;
int max_pwm = 75;

/*--------------------------------rfid 객체 생성--------------------------------*/

MFRC522 rfid(SS_PIN, RST_PIN);

/*--------------------------------함수 선언--------------------------------*/

void receive_json(const String& msg);
void send_obstacle(float distance_cm, bool detected, const char* position);
void send_arrived(const char* position, const char* gate_id);
bool isSameUID(byte* uid1, byte* uid2);
bool checkAndPrintUID(byte* uid);

/*--------------------------------------------------------------------------------*/

void setup() 
{
  Serial.begin(115200);

  // 모터 핀 설정
  pinMode(MOTOR1_IN1, OUTPUT);
  pinMode(MOTOR1_IN2, OUTPUT);
  pinMode(MOTOR2_IN3, OUTPUT);
  pinMode(MOTOR2_IN4, OUTPUT);

  ledcSetup(PWM_CHANNEL_LEFT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(MOTOR12_EN, PWM_CHANNEL_LEFT);
  ledcSetup(PWM_CHANNEL_RIGHT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(MOTOR34_EN, PWM_CHANNEL_RIGHT);
  
  // 초음파센서 핀 설정
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  //서보모터 초기 설정
  unloading_servo.attach(SERVO_PIN);
  unloading_servo.write(SERVO_INIT_ANGLE);  // 초기 위치

  // WiFi 연결
  WiFi.begin(ssid, password);
  Serial.println("WiFi 연결 중...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅Wi-Fi 연결 완료!");

  // 서버 접속 시도
  reconnectToServer();

  // RFID 초기화
  SPI.begin(18, 19, 23, 21);  // SCK, MISO, MOSI, SS
  rfid.PCD_Init();
  Serial.println("✅RC522 RFID 리더기 시작됨!");

  // 시간 동기화
  configTime(9 * 3600, 0, "pool.ntp.org", "time.nist.gov");
  Serial.println("⏳ 시간 동기화 대기 중...");
  while (time(nullptr) < 100000) 
  {
    delay(100);
    Serial.println("...");
  }
  Serial.println("✅시간 동기화 완료!");

  // 미션 요청 자동 전송
  delay(2000);  // 안정화 대기
  send_assign_mission();

}

void loop() 
{
  reconnectToServer();

  // ✅ 수신 메시지 처리
  if (client && client.available()) {
    incoming_msg = client.readStringUntil('\n');
    incoming_msg.trim();
    // Serial.println("========== 📩 [서버 메시지 수신] ==========");
    // Serial.println(incoming_msg);
    // Serial.println("===========================================");
    receive_json(incoming_msg);
  }

  // ✅ 현재 시간 갱신
  unsigned long current_time = millis();

  // ✅ 주기적인 미션 체크
  if (current_time - last_mission_check >= MISSION_CHECK_INTERVAL) 
  {
    last_mission_check = current_time;
    if (current_position == "UNKNOWN") // 원래는 같이 있었음|| current_position == "STANDBY"
    {
      Serial.println("[🔄 미션 체크] 새로운 미션 확인 중...");
      send_assign_mission();
    }
  }

    // ✅ 주행 제어
  obstacle_block = obstacle_detected();
  if (run_command && !obstacle_block && !battery_empty)
  {
    //Serial.println("run");
    line_trace();
    //send_obstacle(last_distance_cm, false, current_position.c_str());
  }
  else if (obstacle_block) 
  {
    Serial.println("stop");
    //Serial.print("Distance: ");
    //Serial.print(distance_cm);
    //Serial.println(" cm");
    stop_motors();
    send_obstacle(last_distance_cm, true, current_position.c_str());
  }

  //적재 시작 지연 처리
  if (wait_start_loading && (current_time - wait_start_loading_time >= 2000)) 
  {
    Serial.println("🕒 적재 시작 메시지 전송 (2초 지연 후)");
    send_start_loading();
    loading_in_progress = true;
    loading_start_time = current_time;
    wait_start_loading = false;
  }
  // 적재 완료 로직 추가 (5초 뒤 자동 전송)
  if (loading_in_progress && (current_time - loading_start_time >= 5000)) 
  {
    Serial.println("✅ 적재 완료 메시지 전송 (5초 경과)");
    send_finish_loading();
    loading_in_progress = false;
  }

  // 언로딩 시작 지연 처리
  if (wait_start_unloading && (current_time - wait_start_unloading_time >= 2000)) 
  {
    start_unloading();
    wait_start_unloading = false;
  }

  // 언로딩 FSM 처리
  handle_unloading(current_time);
    
  // RFID 체크
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) 
  {
    return;
  }

  // Serial.print("UID: ");
  // for (byte i = 0; i < rfid.uid.size; i++) {
  //   if (rfid.uid.uidByte[i] < 0x10) Serial.print("0");
  //   Serial.print(rfid.uid.uidByte[i], HEX);
  //   if (i < rfid.uid.size - 1) Serial.print("-");
  // }
  // Serial.println();

  // UID 확인 및 서버 전송
  checkAndPrintUID(rfid.uid.uidByte);

  // 🪫 10초마다 배터리 감소
  if (current_time - last_battery_drop >= BATTERY_DROP_INTERVAL) {
    last_battery_drop = current_time;

    if (battery_level > 0) {
      battery_level -= 5;
      if (battery_level <= 0) {
        battery_level = 0;
        battery_empty = true;
        run_command = false;
        stop_motors();
        Serial.println("❌ 배터리 소진 → 트럭 정지");
      }

      Serial.print("🪫 배터리 감소됨: ");
      Serial.print(battery_level);
      Serial.println("%");
    }
  }

  // 📤 5초마다 서버에 배터리 상태 전송
  if (current_time - last_battery_report >= BATTERY_REPORT_INTERVAL) {
    last_battery_report = current_time;
    send_battery_status();
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

/*------------------------------- 수신 처리--------------------------------*/

void receive_json(const String& msg)
{
  Serial.println("📩 [디버깅] receive_json() 호출됨");  // ✔️

  Serial.print("📩 [디버깅] 원본 메시지: ");
  Serial.println(msg);  // ✔️

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, msg);

  if (err)
  {
    Serial.println("⚠️ [JSON 파싱 실패]");
    Serial.println(err.c_str());  // ✔️ 구체적인 파싱 에러 출력
    return;
  }

  Serial.println("✅ [JSON 파싱 성공]");  // ✔️

  const char* cmd = doc["cmd"];
  Serial.print("📩 [디버깅] 파싱된 명령어: ");
  Serial.println(cmd);

  if (last_cmd == String(cmd))
  {
    Serial.print("[⏭️ 중복 명령 무시] 이미 처리한 명령: ");  
    Serial.println(cmd);
    return;
  }

  last_cmd = String(cmd);
  
  // 명령 처리
  if (strcmp(cmd, "SET_SPEED") == 0) 
  {
    Serial.println("[디버깅] SET_SPEED 명령 처리 시작");
  } 
  else if (strcmp(cmd, "RUN") == 0) 
  {
    Serial.println("[✅ 디버깅] RUN 명령 수신됨!");
    run_command = true;
  } 
  else if (strcmp(cmd, "STOP") == 0) 
  {
    Serial.println("[⛔ 디버깅] STOP 명령 수신됨!");
    run_command = false;
    stop_motors();
  } 
  else if (strcmp(cmd, "GATE_OPENED") == 0) 
  {
  const char* gate_id = doc["payload"]["gate_id"];
  Serial.print("[🚪 게이트 열림 감지] : ");
  Serial.println(gate_id);

  send_gateopen_message(gate_id);  // 응답 전송
  run_command = true;
  }
  else if (strcmp(cmd, "MISSION_ASSIGNED") == 0) 
  {
    const char* target = doc["payload"]["source"];
    mission_target = String(target);
    Serial.print("[📦 미션 할당됨] 목표 위치: ");
    Serial.println(mission_target);
    run_command = true;
  }
  else if (strcmp(cmd, "NO_MISSION") == 0) 
  {
    Serial.println("📭 [서버 응답] 미션 없음 → 대기 상태 유지");
    run_command = false;
    mission_target = "";
  }
  else 
  {
    Serial.print("[ℹ️ 디버깅] 알 수 없는 명령: ");
    Serial.println(cmd);
  }
}


/*-------------------------------- 송신 처리 --------------------------------*/

// JSON 송신 함수
void send_json(const char* cmd, JsonObject payload)
{
  StaticJsonDocument<256> doc;

  // 공통 메시지 구조
  doc["sender"] = truck_id;
  doc["receiver"] = "SERVER";
  doc["cmd"] = cmd;
  doc["payload"] = payload;
  
  // 서버 연결 확인 후 메시지 전송
  if (client && client.connected())
  {
    serializeJson(doc, client);
    client.print("\n");
    Serial.println("[📤 송신] 메시지 전송:");
    serializeJsonPretty(doc, Serial);
    Serial.println();
  }
  else
  {
    Serial.println("[❌ 오류] 서버와 연결되지 않음 (메시지 전송 실패)");
  }
}

// 미션 요청 메시지 (ASSIGN_MISSION)
void send_assign_mission() 
{
  StaticJsonDocument<256> doc;
  JsonObject payload = doc.createNestedObject("payload");
  send_json("ASSIGN_MISSION", payload);
}

void send_gateopen_message(const char* gate_id)
{
  StaticJsonDocument<256> doc;
  JsonObject payload = doc.createNestedObject("payload");

  payload["gate_id"] = gate_id;
  payload["position"] = current_position;
  payload["timestamp"] = getISOTime();

  send_json("ACK_GATE_OPENED", payload);
}


// 도착 메시지 (ARRIVED)
void send_arrived(const char* position, const char* gate_id) 
{
  StaticJsonDocument<256> doc;
  JsonObject payload = doc.createNestedObject("payload");
  payload["position"] = position;
  payload["gate_id"] = gate_id;
  payload["timestamp"] = getISOTime();
  send_json("ARRIVED", payload);
}

// 장애물 감지 메시지 (OBSTACLE)
void send_obstacle(float distance_cm, bool detected, const char* position) 
{

  if (detected == prev_obstacle_state) return;

  prev_obstacle_state = detected;

  StaticJsonDocument<256> doc;
  JsonObject payload = doc.createNestedObject("payload");

  payload["position"] = position;
  payload["distance_cm"] = distance_cm;
  payload["timestamp"] = getISOTime();
  payload["detected"] = detected ? "DETECTED" : "CLEARED";
  
  send_json("OBSTACLE", payload);
}

//로딩 시작 메세지
void send_start_loading() 
{
  StaticJsonDocument<128> doc;
  JsonObject payload = doc.createNestedObject("payload");

  payload["position"] = current_position;
  payload["timestamp"] = getISOTime();

  send_json("START_LOADING", payload);
}

void send_finish_loading() 
{
  StaticJsonDocument<128> doc;
  JsonObject payload = doc.createNestedObject("payload");

  payload["position"] = current_position;
  payload["timestamp"] = getISOTime();

  send_json("FINISH_LOADING", payload);
}
//언로딩 시작 메세지
void send_start_unloading() {
  StaticJsonDocument<128> doc;
  JsonObject payload = doc.createNestedObject("payload");

  payload["position"] = current_position;
  payload["timestamp"] = getISOTime();

  send_json("START_UNLOADING", payload);
}

void send_finish_unloading() {
  StaticJsonDocument<128> doc;
  JsonObject payload = doc.createNestedObject("payload");

  payload["position"] = current_position;
  payload["timestamp"] = getISOTime();

  send_json("FINISH_UNLOADING", payload);
}


void send_battery_status() {
  StaticJsonDocument<128> doc;
  JsonObject payload = doc.createNestedObject("payload");

  payload["battery_level"] = battery_level;
  payload["timestamp"] = getISOTime();

  send_json("BATTERY", payload);
}


/*--------------------------------라인트레이서 제어--------------------------------*/

void line_trace() {
  l_sensor_val = analogRead(LEFT_SENSOR);
  r_sensor_val = analogRead(RIGHT_SENSOR);

  Serial.print("L: "); Serial.print(l_sensor_val);
  Serial.print(" R: "); Serial.println(r_sensor_val);

  error = l_sensor_val - r_sensor_val;


  // ⬇ PID 제어 계산
  integral += error;
  derivative = error - last_error;
  PID_control = Kp * error + Ki * integral + Kd * derivative;


  last_error = error;

  R_PWM = speed_limit(avg_PWM - PID_control, 0, max_pwm);
  L_PWM = speed_limit(avg_PWM + PID_control, 0, max_pwm);

  left_motor_f(L_PWM);
  right_motor_f(R_PWM);
}

void stop_motors() {
  ledcWrite(PWM_CHANNEL_LEFT, 0);
  ledcWrite(PWM_CHANNEL_RIGHT, 0);
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

int speed_limit(int val, int minVal, int maxVal) {
  if (val < minVal) return minVal;
  if (val > maxVal) return maxVal;
  return val;
}

/*--------------------------------초음파 기반 장애물 감지--------------------------------*/

// 장애물 감지 여부
bool obstacle_detected() {
  long duration;
  float distance_cm;

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  duration = pulseIn(ECHO_PIN, HIGH); 
  if (duration == 0)
  {
    //Serial.println("Hello");
    return false;  // 실패했으면 장애물 없음
  }
  
  distance_cm = duration * 0.034 / 2.0;  // 거리 계산
  last_distance_cm = distance_cm;  // 전역 변수 업데이트

  return distance_cm < 12.0;  // 10cm 이내면 true
}
/*--------------------------------언로딩 처리 함수--------------------------------*/

void start_unloading() {
  Serial.println("🕒 언로딩 시작 메시지 전송 (2초 지연 후)");
  send_start_unloading();
  unloading_in_progress = true;
  unloading_stage = 1;
  unloading_stage_time = millis();
}


void handle_unloading(unsigned long current_time) {
  if (!unloading_in_progress) return;

  if (unloading_stage == 1 && current_time - unloading_stage_time >= 0) 
  {
    Serial.println("✅ 언로딩 서보모터 → 90도 (내리기)");
    unloading_servo.write(SERVO_DROP_ANGLE);
    unloading_stage_time = current_time;
    unloading_stage = 2;
  }
  else if (unloading_stage == 2 && current_time - unloading_stage_time >= 2000) 
  {
    Serial.println("✅ 언로딩 서보모터 → 170도 (올리기)");
    unloading_servo.write(SERVO_INIT_ANGLE);
    unloading_stage_time = current_time;
    unloading_stage = 3;
  }
  else if (unloading_stage == 3 && current_time - unloading_stage_time >= 1000) 
  {
    Serial.println("✅ 언로딩 완료 메시지 전송");
    send_finish_unloading();
    unloading_in_progress = false;
    unloading_stage = 0;
  }
}


/*--------------------------------UID 관련 함수--------------------------------*/

bool isSameUID(byte *uid1, byte *uid2) 
{
  for (byte i = 0; i < 4; i++) 
  {
    if (uid1[i] != uid2[i]) return false;
  }
  return true;
}

bool checkAndPrintUID(byte* uid) 
{
  for (int i = 0; i < numRegistered; i++) {
    if (isSameUID(uid, registeredCards[i].uid)) {
      const char* desc = registeredCards[i].description;

      Serial.println("✅ 등록된 카드입니다!");
      Serial.print("📌 ");
      Serial.println(desc);

      // 위치 갱신 및 도착 메시지 전송
      current_position = String(desc);

      if (strcmp(desc, "CHECKPOINT_A") == 0) 
      {
        send_arrived("CHECKPOINT_A", "GATE_A");
        run_command = false;
      } 
      else if (strcmp(desc, "CHECKPOINT_B") == 0) 
      {
        send_arrived("CHECKPOINT_B", "GATE_A");
      } 
      else if (strcmp(desc, "CHECKPOINT_C") == 0) 
      {
        send_arrived("CHECKPOINT_C", "GATE_B");
        run_command = false;
      } 
      else if (strcmp(desc, "CHECKPOINT_D") == 0) 
      {
        send_arrived("CHECKPOINT_D", "GATE_B");
      }
      else if (strcmp(desc, "load_A") == 0)                        //load_A
      {
        send_arrived("load_A", "LOAD_A");
        // 현재 목적지가 load_A인 경우에만 적재 시작 대기
        if ((mission_target == "LOAD_A")or(mission_target == "load_A")) 
        {
          Serial.println(mission_target);
          Serial.println("Debug1");
          wait_start_loading = true;
          wait_start_loading_time = millis();
        }
      }
      else if (strcmp(desc, "load_B") == 0)                       //load_B
      {
        send_arrived("load_B", "LOAD_B");

        if ((mission_target == "load_B") or (mission_target == "LOAD_B")) 
        {
          wait_start_loading = true;
          wait_start_loading_time = millis();
        }
      }
      else if (strcmp(desc, "BELT") == 0) 
      {
        send_arrived("BELT", "BELT");
        wait_start_unloading = true;
        wait_start_unloading_time = millis();
        
      }
      else if (strcmp(desc, "STANDBY") == 0) 
      {
        send_arrived("STANDBY", "STANDBY");
        run_command = false;

        send_assign_mission(); 
      } 


      // 🎯 목적지에 도달한 경우 멈춤
      if (mission_target != "" && mission_target == String(desc)) {
        Serial.println("🎯 [도착 확인] 목적지 도달 → 주행 중지");
        run_command = false;
        stop_motors();
      }

      return true;
    }
  }

  Serial.println("❌ 등록되지 않은 카드입니다!");
  return false;  // 등록되지 않음
}

/*-------------------------------유틸 함수--------------------------------*/

String getISOTime() 
{
  time_t now = time(nullptr);
  struct tm* t = localtime(&now);
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", t);
  return String(buffer);
}

void reconnectToServer() 
{
  if (!client.connected()) 
  {
    Serial.print("🌐 서버 접속 시도 중...");
    if (client.connect(serverIP, serverPort)) 
    {
      Serial.println("✅ 접속 성공!");
    } 
    else 
    {
      Serial.println("❌ 접속 실패");
    }
  }
}