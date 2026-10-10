#pragma once

#define ESP32_DEVKIT_V1 1

static constexpr uint8_t DS18B20_PIN = 4;
static constexpr uint8_t MQ135_AOUT_PIN = 35;
static constexpr uint8_t REED_SWITCH_PIN = 27;
static constexpr uint8_t HX711_DT_PIN = 16;
static constexpr uint8_t HX711_SCK_PIN = 17;
static constexpr uint8_t TTP223_PIN = 32;
static constexpr uint8_t FAN_PIN = 25;
static constexpr uint8_t BUZZER_PIN = 26;
static constexpr uint8_t RED_LED_PIN = 18;
static constexpr uint8_t GREEN_LED_PIN = 19;

static constexpr float TEMP_HIGH_C = 7.0f;
static constexpr float TEMP_WARNING_C = 6.0f;
static constexpr float GAS_RISE_DELTA = 10.0f;
static constexpr float LOW_INVENTORY_KG = 2.5f;
static constexpr float DOOR_OPEN_TIMEOUT_S = 180.0f;

static constexpr uint8_t MAX_OFFLINE_RING_BUFFER = 32;
static constexpr uint32_t WIFI_RETRY_MS = 5000UL;
static constexpr uint32_t WATCHDOG_MS = 60000UL;
