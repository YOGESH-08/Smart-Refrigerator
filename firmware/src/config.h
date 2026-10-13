#pragma once

#include <Arduino.h>
#include "device_config.h"

static constexpr uint8_t DS18B20_PIN = 4;
static constexpr uint8_t MQ135_AOUT_PIN = 34;
static constexpr uint8_t REED_SWITCH_PIN = 27;
static constexpr uint8_t TTP223_PIN = 14;
static constexpr uint8_t RFID_SS_PIN = 5;
static constexpr uint8_t RFID_RST_PIN = 22;
static constexpr uint8_t FAN_PIN = 26;
static constexpr uint8_t BUZZER_PIN = 13;
static constexpr uint8_t RED_LED_PIN = 15;
static constexpr uint8_t GREEN_LED_PIN = 21;

static constexpr float TEMP_HIGH_C = 29.0f;
static constexpr uint32_t ALARM_MUTE_MS = 30000UL;
static constexpr uint32_t DOOR_ALARM_DELAY_MS = 180000UL;
// GPIO27 uses INPUT_PULLUP and an active-low reed switch.
static constexpr bool DOOR_SENSOR_VERIFIED = true;
static constexpr bool ENABLE_DOOR_ALARM = true;

static constexpr size_t MAX_OFFLINE_RING_BUFFER = 32;
static constexpr uint32_t WIFI_RETRY_INITIAL_MS = 2000UL;
static constexpr uint32_t WIFI_RETRY_MAX_MS = 60000UL;
static constexpr uint32_t READ_INTERVAL_MS = 1000UL;
