#pragma once

#include <Arduino.h>
#include "config.h"
#include "sensors/sensors.h"

enum class FridgeState : uint8_t {
  NORMAL = 0,
  WARNING = 1,
  DOOR_ALERT = 2
};

class FridgeStateMachine {
 public:
  FridgeState update(const SensorReadings& sample, uint32_t now_ms) {
    if (sample.door_open) {
      if (!door_open_) {
        door_open_since_ms_ = now_ms;
      }
      door_open_ = true;
    } else {
      door_open_ = false;
      door_open_since_ms_ = 0;
    }

    if (sample.temperature_valid) temperature_warning_ = sample.temperature_c > TEMP_HIGH_C;
    const bool door_alert = ENABLE_DOOR_ALARM && door_open_ &&
                            (now_ms - door_open_since_ms_ >= DOOR_ALARM_DELAY_MS);
    state_ = door_alert ? FridgeState::DOOR_ALERT
                        : (temperature_warning_ ? FridgeState::WARNING : FridgeState::NORMAL);
    return state_;
  }

  bool warningActive() const {
    return temperature_warning_;
  }

 private:
  FridgeState state_ = FridgeState::NORMAL;
  bool door_open_ = false;
  bool temperature_warning_ = false;
  uint32_t door_open_since_ms_ = 0;
};
