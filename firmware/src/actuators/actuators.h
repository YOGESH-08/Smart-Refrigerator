#pragma once

#include <Arduino.h>
#include "../config.h"

struct ActuatorStates {
  bool alarm_active;
  bool alarm_muted;
  bool fan_on;
  bool red_led_on;
  bool green_led_on;
  bool buzzer_on;
};

class ActuatorController {
 public:
  void begin() {
    pinMode(FAN_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(RED_LED_PIN, OUTPUT);
    pinMode(GREEN_LED_PIN, OUTPUT);
    digitalWrite(FAN_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(RED_LED_PIN, LOW);
    digitalWrite(GREEN_LED_PIN, HIGH);
  }

  ActuatorStates applyState(bool warning, bool door_alert, bool sound_silenced, bool temperature_valid) {
    const bool alert = warning || door_alert;
    const bool fan_on = warning;
    const bool buzzer_on = alert && !sound_silenced;
    const bool red_led_on = alert;
    const bool green_led_on = !alert && temperature_valid;
    digitalWrite(FAN_PIN, fan_on ? HIGH : LOW);
    digitalWrite(BUZZER_PIN, buzzer_on ? HIGH : LOW);
    digitalWrite(RED_LED_PIN, red_led_on ? HIGH : LOW);
    digitalWrite(GREEN_LED_PIN, green_led_on ? HIGH : LOW);
    return {alert, alert && sound_silenced, fan_on, red_led_on, green_led_on, buzzer_on};
  }
};
