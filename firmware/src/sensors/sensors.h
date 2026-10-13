#pragma once

#include <Arduino.h>
#include <DallasTemperature.h>
#include <OneWire.h>

#include "../config.h"

struct SensorReadings {
  float temperature_c = NAN;
  uint16_t gas_adc_raw = 0;
  bool temperature_valid = false;
  bool gas_valid = false;
  bool door_open = false;
  bool silence_pressed = false;
  bool touch_pressed = false;
  bool rfid_reader_ok = false;
  bool door_sensor_verified = false;
  bool alarm_active = false;
  bool alarm_muted = false;
  bool fan_on = false;
  bool red_led_on = false;
  bool green_led_on = false;
  bool buzzer_on = false;
  uint16_t mute_remaining_s = 0;
};

class SensorSubsystem {
 public:
  void begin() {
    pinMode(MQ135_AOUT_PIN, INPUT);
    pinMode(REED_SWITCH_PIN, INPUT_PULLUP);
    pinMode(TTP223_PIN, INPUT);
    analogReadResolution(12);
    sensors_.begin();
    sensors_.setWaitForConversion(false);
    sensors_.requestTemperatures();
    conversion_started_ms_ = millis();
  }

  SensorReadings read() {
    const uint32_t now = millis();
    if (now - conversion_started_ms_ >= conversion_time_ms_) {
      const float reading = sensors_.getTempCByIndex(0);
      if (reading != DEVICE_DISCONNECTED_C && !isnan(reading) && reading >= -50.0f && reading <= 100.0f) {
        temperature_c_ = reading;
        temperature_valid_ = true;
      } else {
        temperature_valid_ = false;
      }
      sensors_.requestTemperatures();
      conversion_started_ms_ = now;
    }

    const uint16_t gas = static_cast<uint16_t>(analogRead(MQ135_AOUT_PIN));
    SensorReadings result;
    result.temperature_c = temperature_c_;
    result.temperature_valid = temperature_valid_;
    result.gas_adc_raw = gas;
    result.gas_valid = gas > 1 && gas < 4094;
    result.door_open = digitalRead(REED_SWITCH_PIN) == LOW;
    result.door_sensor_verified = DOOR_SENSOR_VERIFIED;
    result.silence_pressed = touchPressed();
    result.touch_pressed = result.silence_pressed;
    return result;
  }

  bool touchPressed() const { return digitalRead(TTP223_PIN) == HIGH; }

 private:
  OneWire one_wire_{DS18B20_PIN};
  DallasTemperature sensors_{&one_wire_};
  uint32_t conversion_started_ms_ = 0;
  static constexpr uint32_t conversion_time_ms_ = 750UL;
  float temperature_c_ = NAN;
  bool temperature_valid_ = false;
};
