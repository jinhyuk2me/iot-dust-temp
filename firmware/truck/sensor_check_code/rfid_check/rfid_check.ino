#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 21     // SDA = GPIO21
#define RST_PIN 22    // RST = GPIO22

MFRC522 rfid(SS_PIN, RST_PIN);

// 등록된 UID (예: 실제 카드 찍어서 확인 후 수정하세요)
byte registeredUID[4] = {0x86, 0x51, 0x0A, 0x05};

void setup() {
  Serial.begin(115200);
  SPI.begin(18, 19, 23, 21);  // SCK, MISO, MOSI, SS(SDA)
  rfid.PCD_Init();
  Serial.println("📡 RC522 RFID 리더기 초기화 완료!");
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  Serial.print("UID 읽음: ");
  for (byte i = 0; i < rfid.uid.size; i++) {
    Serial.print(rfid.uid.uidByte[i], HEX);
    Serial.print(" ");
  }
  Serial.println();

  if (isUIDMatched(rfid.uid.uidByte, rfid.uid.size)) {
    Serial.println("✅ 등록된 카드입니다!");
  } else {
    Serial.println("❌ 등록되지 않은 카드입니다!");
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

bool isUIDMatched(byte *uid, byte length) {
  if (length != 4) return false;
  for (byte i = 0; i < 4; i++) {
    if (uid[i] != registeredUID[i]) return false;
  }
  return true;
}