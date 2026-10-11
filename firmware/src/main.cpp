#include <Arduino.h>
#include <WiFi.h>
#include <SPI.h>
#include <MFRC522.h>
#include <esp_idf_version.h>
#include <esp_task_wdt.h>

#include "config.h"
#include "actuators/actuators.h"
#include "net/network.h"
#include "sensors/sensors.h"
#include "state_machine.h"

namespace {
  SensorSubsystem sensors;
  ActuatorController actuators;
  NetworkClient network;
  FridgeStateMachine state_machine;
  SensorReadings ring_buffer[MAX_OFFLINE_RING_BUFFER];
  uint32_t ring_door_seconds[MAX_OFFLINE_RING_BUFFER];
  size_t ring_head = 0;
  size_t ring_count = 0;
  bool sound_silenced = false;
  bool door_open = false;
  uint32_t door_open_since_ms = 0;
  uint32_t last_read_ms = 0;
  uint32_t last_wifi_attempt_ms = 0;
  uint32_t wifi_retry_ms = WIFI_RETRY_INITIAL_MS;
  uint32_t boot_ms = 0;
  uint32_t mute_until_ms = 0;
  bool touch_was_pressed = false;
  uint32_t last_command_poll_ms = 0;
  uint32_t last_network_action_ms = 0;
  uint32_t network_backoff_ms = 500UL;
  uint32_t last_rfid_wait_log_ms = 0;
  bool rfid_reader_ok = false;
  bool pending_touch_ack = false;
  bool send_rfid_next = true;
  uint32_t dropped_readings_since_log = 0;
  uint32_t last_drop_log_ms = 0;
  SensorReadings current_sample{};
  FridgeState current_state = FridgeState::NORMAL;
  ActuatorStates current_actuators{};
  MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);
  static constexpr size_t RFID_QUEUE_CAPACITY = 8;
  String rfid_queue[RFID_QUEUE_CAPACITY];
  size_t rfid_head = 0;
  size_t rfid_count = 0;

  bool isRecognizedRfidVersion(byte version) {
    // Versions reported by the MFRC522 library for known silicon/compatible clones.
    // 0x00, 0xFF, and undocumented values (including 0x82) are not proof of a working reader.
    return version == 0x88 || version == 0x90 || version == 0x91 || version == 0x92;
  }

  void configureWatchdog() {
#if ESP_IDF_VERSION_MAJOR >= 5
    esp_task_wdt_config_t watchdog_config = {};
    watchdog_config.timeout_ms = 10000;
    watchdog_config.idle_core_mask = (1 << portNUM_PROCESSORS) - 1;
    watchdog_config.trigger_panic = true;
    const esp_err_t init_result = esp_task_wdt_init(&watchdog_config);
#else
    const esp_err_t init_result = esp_task_wdt_init(10, true);
#endif
    if (init_result != ESP_OK && init_result != ESP_ERR_INVALID_STATE) {
      Serial.printf("Watchdog initialization failed: %d\\n", init_result);
    }
    const esp_err_t add_result = esp_task_wdt_add(nullptr);
    if (add_result != ESP_OK && add_result != ESP_ERR_INVALID_STATE) {
      Serial.printf("Watchdog task registration failed: %d\\n", add_result);
    }
  }
  void enqueueReading(const SensorReadings& sample, uint32_t door_open_seconds) {
    if (ring_count == MAX_OFFLINE_RING_BUFFER) {
      ++dropped_readings_since_log;
      const uint32_t now = millis();
      if (now - last_drop_log_ms >= 30000UL) {
        Serial.printf("Offline telemetry queue full; dropped %lu old readings in the last 30s\n",
                      static_cast<unsigned long>(dropped_readings_since_log));
        dropped_readings_since_log = 0;
        last_drop_log_ms = now;
      }
      ring_head = (ring_head + 1) % MAX_OFFLINE_RING_BUFFER;
      --ring_count;
    }
    const size_t tail = (ring_head + ring_count) % MAX_OFFLINE_RING_BUFFER;
    ring_buffer[tail] = sample;
    ring_door_seconds[tail] = door_open_seconds;
    ++ring_count;
  }

  void applyLocalControl(uint32_t now_ms) {
    const bool door_alert = ENABLE_DOOR_ALARM && current_state == FridgeState::DOOR_ALERT;
    const bool warning = state_machine.warningActive();
    const bool alert = door_alert || warning;
    const bool touch_pressed = sensors.touchPressed();
    if (touch_pressed && !touch_was_pressed && alert) {
      mute_until_ms = now_ms + ALARM_MUTE_MS;
      pending_touch_ack = true;
      Serial.println("Touch alert: buzzer muted for 30s; alert acknowledgement queued");
    }
    touch_was_pressed = touch_pressed;
    if (!alert || (mute_until_ms && static_cast<int32_t>(now_ms - mute_until_ms) >= 0)) {
      mute_until_ms = 0;
    }
    sound_silenced = alert && mute_until_ms != 0;
    const ActuatorStates previous_actuators = current_actuators;
    current_actuators = actuators.applyState(warning, door_alert, sound_silenced,
                                              current_sample.temperature_valid);
    current_sample.alarm_active = current_actuators.alarm_active;
    current_sample.alarm_muted = current_actuators.alarm_muted;
    current_sample.fan_on = current_actuators.fan_on;
    current_sample.red_led_on = current_actuators.red_led_on;
    current_sample.green_led_on = current_actuators.green_led_on;
    current_sample.buzzer_on = current_actuators.buzzer_on;
    current_sample.mute_remaining_s = sound_silenced
        ? static_cast<uint16_t>((mute_until_ms - now_ms + 999UL) / 1000UL) : 0;
    if (previous_actuators.alarm_active != current_actuators.alarm_active ||
        previous_actuators.buzzer_on != current_actuators.buzzer_on ||
        previous_actuators.fan_on != current_actuators.fan_on) {
      Serial.printf("Alarm=%s buzzer=%s fan=%s\n", alert ? "ACTIVE" : "CLEAR",
                    current_actuators.buzzer_on ? "ON" : "OFF",
                    current_actuators.fan_on ? "ON" : "OFF");
    }
  }

  void scanRfidCard() {
    if (!rfid.PICC_IsNewCardPresent()) {
      const uint32_t now = millis();
      if (now - last_rfid_wait_log_ms >= 5000UL) {
        last_rfid_wait_log_ms = now;
        Serial.printf("RFID %s; NO CARD PRESENT; hold a 13.56 MHz tag over the reader antenna (SS=%u SCK=18 MOSI=23 MISO=19 RST=%u)\n",
                      rfid_reader_ok ? "reader ready" : "READER NOT DETECTED", RFID_SS_PIN, RFID_RST_PIN);
      }
      return;
    }
    Serial.println("RFID: card detected; reading UID...");
    if (!rfid.PICC_ReadCardSerial()) {
      Serial.println("RFID: UID read failed; keep the tag steady and check 3.3V, GND, and SPI wiring");
      return;
    }
    String uid;
    for (byte index = 0; index < rfid.uid.size; ++index) {
      if (index) uid += ':';
      if (rfid.uid.uidByte[index] < 0x10) uid += '0';
      uid += String(rfid.uid.uidByte[index], HEX);
    }
    uid.toUpperCase();
    Serial.printf("RFID UID READ SUCCESS: %s | type=", uid.c_str());
    Serial.print(MFRC522::PICC_GetTypeName(rfid.PICC_GetType(rfid.uid.sak)));
    Serial.printf(" | bytes=%u\n", static_cast<unsigned>(rfid.uid.size));
    Serial.flush();
    if (rfid_count == RFID_QUEUE_CAPACITY) {
      rfid_head = (rfid_head + 1) % RFID_QUEUE_CAPACITY;
      --rfid_count;
      Serial.println("RFID offline queue full; dropping oldest scan");
    }
    rfid_queue[(rfid_head + rfid_count) % RFID_QUEUE_CAPACITY] = uid;
    ++rfid_count;
    Serial.printf("RFID: UID queued for dashboard upload; pending scans=%u\n",
                  static_cast<unsigned>(rfid_count));
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
  }

  bool flushOneRfidScan() {
    if (!network.isConnected() || rfid_count == 0) return false;
    if (network.sendRfidScan(rfid_queue[rfid_head])) {
      rfid_head = (rfid_head + 1) % RFID_QUEUE_CAPACITY;
      --rfid_count;
      return true;
    }
    return false;
  }

  void reconnectWiFi(uint32_t now_ms) {
    if (network.isConnected() || now_ms - last_wifi_attempt_ms < wifi_retry_ms) {
      return;
    }
    Serial.printf("WiFi reconnect attempt; retry delay is %lu ms\n",
                  static_cast<unsigned long>(wifi_retry_ms));
    last_wifi_attempt_ms = now_ms;
    WiFi.reconnect();
    const uint32_t next_retry_ms = wifi_retry_ms * static_cast<uint32_t>(2);
    wifi_retry_ms = next_retry_ms < WIFI_RETRY_MAX_MS ? next_retry_ms : WIFI_RETRY_MAX_MS;
  }

  bool flushOneReading() {
    if (!network.isConnected() || ring_count == 0) {
      return false;
    }
    if (network.sendReading(ring_buffer[ring_head], ring_door_seconds[ring_head],
                            (millis() - boot_ms) / 1000UL)) {
      ring_head = (ring_head + 1) % MAX_OFFLINE_RING_BUFFER;
      --ring_count;
      return true;
    }
    return false;
  }
}

void setup() {
  Serial.begin(115200);
  boot_ms = millis();
  actuators.begin();
  sensors.begin();
  network.begin();
  SPI.begin(18, 19, 23, RFID_SS_PIN);
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(MFRC522::RxGain_max);
  rfid.PCD_AntennaOn();
  delay(4);
  const byte rfid_version = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  last_wifi_attempt_ms = boot_ms;
  configureWatchdog();
  Serial.printf("Smart Refrigerator %s booted as %s\n", FIRMWARE_VERSION, DEVICE_ID);
  Serial.printf("Pins: DS18B20=GPIO%u MQ135_AO=GPIO%u REED=GPIO%u TTP223=GPIO%u | RC522 SS/SDA=GPIO%u SCK=GPIO18 MOSI=GPIO23 MISO=GPIO19 RST=GPIO%u | FAN=GPIO%u BUZZER=GPIO%u RED_LED=GPIO%u GREEN_LED=GPIO%u\n",
                DS18B20_PIN, MQ135_AOUT_PIN, REED_SWITCH_PIN, TTP223_PIN,
                RFID_SS_PIN, RFID_RST_PIN, FAN_PIN, BUZZER_PIN, RED_LED_PIN, GREEN_LED_PIN);
  rfid_reader_ok = isRecognizedRfidVersion(rfid_version);
  Serial.printf("RC522 version register: 0x%02X%s\n", rfid_version,
                rfid_reader_ok ? " (recognized response; card reading still needs testing)"
                               : " (unrecognized/no response; check 3.3V, GND, and SPI contacts)");
}

void loop() {
  const unsigned long now_ms = millis();

  if (now_ms - last_read_ms >= READ_INTERVAL_MS) {
    last_read_ms = now_ms;
    current_sample = sensors.read();
    SensorReadings& sample = current_sample;
    sample.rfid_reader_ok = rfid_reader_ok;
    if (sample.door_open && !door_open) {
      door_open_since_ms = now_ms;
    } else if (!sample.door_open) {
      door_open_since_ms = 0;
    }
    door_open = sample.door_open;
    const uint32_t door_open_seconds =
        door_open ? (now_ms - door_open_since_ms) / 1000UL : 0;
    current_state = state_machine.update(sample, now_ms);
    applyLocalControl(now_ms);
    enqueueReading(sample, door_open_seconds);

    Serial.printf("Sensors: temp=%s C [GPIO%u] | MQ135_AO=%u/4095 [GPIO%u] | reed=%s raw=%s [GPIO%u] | touch=%s raw=%s [GPIO%u] || Outputs: alarm=%s buzzer=%s [GPIO%u=%s] fan=%s [GPIO%u] LEDs=R:%s/G:%s || queue=%u\n",
                  sample.temperature_valid ? String(sample.temperature_c, 2).c_str() : "SENSOR_ERROR",
                  DS18B20_PIN, sample.gas_adc_raw, MQ135_AOUT_PIN,
                  sample.door_open ? "open" : "closed", digitalRead(REED_SWITCH_PIN) == LOW ? "LOW" : "HIGH", REED_SWITCH_PIN,
                  sample.silence_pressed ? "pressed" : "released", digitalRead(TTP223_PIN) == HIGH ? "HIGH" : "LOW", TTP223_PIN,
                  sample.alarm_active ? "ACTIVE" : "CLEAR", sample.buzzer_on ? "ON" : "OFF", BUZZER_PIN,
                  digitalRead(BUZZER_PIN) == HIGH ? "HIGH" : "LOW",
                  sample.fan_on ? "ON" : "OFF", FAN_PIN,
                  sample.red_led_on ? "ON" : "OFF", sample.green_led_on ? "ON" : "OFF",
                  static_cast<unsigned>(ring_count));
    if (network.isConnected()) {
      wifi_retry_ms = WIFI_RETRY_INITIAL_MS;
    }
  }

  applyLocalControl(now_ms);
  scanRfidCard();
  reconnectWiFi(now_ms);
  const bool command_poll_due = now_ms - last_command_poll_ms >= 2000UL;
  const bool network_work_pending = pending_touch_ack || command_poll_due || rfid_count > 0 || ring_count > 0;
  if (network.isConnected() && network_work_pending &&
      static_cast<int32_t>(now_ms - last_network_action_ms) >= 0) {
    last_network_action_ms = now_ms;
    bool failed = false;
    if (pending_touch_ack) {
      if (network.acknowledgeCurrentAlert()) pending_touch_ack = false;
      else failed = true;
    } else if (command_poll_due) {
      last_command_poll_ms = now_ms;
      bool mute_command = false;
      failed = !network.pollMuteCommand(mute_command);
      if (mute_command) {
        mute_until_ms = now_ms + ALARM_MUTE_MS;
        Serial.println("Dashboard command: buzzer muted for 30s");
        applyLocalControl(now_ms);
      }
    } else if (rfid_count > 0 && ring_count > 0) {
      if (send_rfid_next) failed = !flushOneRfidScan();
      else failed = !flushOneReading();
      send_rfid_next = !send_rfid_next;
    } else if (rfid_count > 0) {
      failed = !flushOneRfidScan();
    } else if (ring_count > 0) {
      failed = !flushOneReading();
    }
    if (failed) {
      network_backoff_ms = network_backoff_ms < 4000UL ? network_backoff_ms * 2UL : 8000UL;
      last_network_action_ms = now_ms + network_backoff_ms;
    } else {
      network_backoff_ms = 500UL;
      last_network_action_ms = now_ms + NETWORK_ACTION_INTERVAL_MS;
    }
  }
  esp_task_wdt_reset();
}
