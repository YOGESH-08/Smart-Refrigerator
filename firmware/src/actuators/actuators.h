#pragma once

#include <Arduino.h>
#include "../config.h"

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

  void applyState(bool door_alert, bool low_inventory, bool warning, bool sound_silenced) {
    const bool fan_on = door_alert || low_inventory || warning;
    digitalWrite(FAN_PIN, fan_on ? HIGH : LOW);
    digitalWrite(RED_LED_PIN, door_alert || low_inventory ? HIGH : LOW);
    digitalWrite(GREEN_LED_PIN, !fan_on ? HIGH : LOW);

    const bool buzzer_on = (door_alert || low_inventory || warning) && !sound_silenced;
    digitalWrite(BUZZER_PIN, buzzer_on ? HIGH : LOW);
  }
};
