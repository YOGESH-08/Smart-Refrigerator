#pragma once

enum class FridgeState : uint8_t {
  NORMAL = 0,
  WARNING = 1,
  DOOR_ALERT = 2,
  LOW_INVENTORY = 3
};

class FridgeStateMachine {
 public:
  explicit FridgeStateMachine() = default;

  FridgeState update(float temperature_c, bool door_open, float weight_kg) {
    if (door_open && temperature_c >= 6.0f) {
      state_ = FridgeState::DOOR_ALERT;
    } else if (weight_kg <= 2.5f) {
      state_ = FridgeState::LOW_INVENTORY;
    } else if (temperature_c >= 7.0f) {
      state_ = FridgeState::WARNING;
    } else {
      state_ = FridgeState::NORMAL;
    }
    return state_;
  }

  FridgeState state() const { return state_; }

 private:
  FridgeState state_ = FridgeState::NORMAL;
};
