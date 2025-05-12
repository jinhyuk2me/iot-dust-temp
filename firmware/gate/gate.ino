#include <Servo.h>

#define GATE_A 9
#define GATE_B 8

Servo gateServo_A;
Servo gateServo_B;

bool AisOpen = false;
bool BisOpen = false;


void openGate_A() 
{
  gateServo_A.write(90);  // 열림 위치
  Serial.println("STATUS:GATE_A:OPENED");
  AisOpen = true;
}

void closeGate_A() 
{
  gateServo_A.write(5);  // 닫힘 위치
  Serial.println("STATUS:GATE_A:CLOSED");
  AisOpen = false;
}

void openGate_B() 
{
  gateServo_B.write(90);  // 열림 위치
  Serial.println("STATUS:GATE_B:OPENED");
  BisOpen = true;
}

void closeGate_B() 
{
  gateServo_B.write(5);  // 닫힘 위치
  Serial.println("STATUS:GATE_B:CLOSED");
  BisOpen = false;
}


void setup() 
{
  Serial.begin(9600);
  gateServo_A.attach(GATE_A);
  gateServo_B.attach(GATE_B);
  closeGate_A();  // 초기 상태 닫힘
  closeGate_B();  // 초기 상태 닫힘
  Serial.println("STATUS:SYSTEM:READY");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "GATE_A_OPEN") {
      openGate_A();
      Serial.println("ACK:GATE_A_OPEN:OK");
    } else if (cmd == "GATE_A_CLOSE") {
      closeGate_A();
      Serial.println("ACK:GATE_A_CLOSE:OK");
    } else if (cmd == "GATE_B_OPEN") {
      openGate_B();
      Serial.println("ACK:GATE_B_OPEN:OK");
    } else if (cmd == "GATE_B_CLOSE") {
      closeGate_B();
      Serial.println("ACK:GATE_B_CLOSE:OK");
    } else {
      Serial.print("ACK:");
      Serial.print(cmd);
      Serial.println(":ERROR");
    }
  }
}