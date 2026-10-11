from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ReadingPayload(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    temperature_c: Optional[float] = Field(default=None, ge=-50.0, le=100.0)
    humidity_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    gas_voc: Optional[float] = Field(default=None, ge=0.0, le=5000.0)
    gas_adc_raw: Optional[int] = Field(default=None, ge=0, le=4095)
    weight_kg: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    door_open: bool = False
    door_open_seconds: Optional[float] = Field(default=None, ge=0.0)
    battery_mv: Optional[float] = Field(default=None, ge=0.0, le=50000.0)
    wifi_rssi_dbm: Optional[int] = Field(default=None, ge=-120, le=0)
    firmware_version: str = Field(default="1.0.0", min_length=1, max_length=32)
    uptime_s: Optional[int] = Field(default=None, ge=0)
    temperature_sensor_ok: Optional[bool] = None
    gas_sensor_ok: Optional[bool] = None
    door_sensor_verified: bool = False
    alarm_active: bool = False
    alarm_muted: bool = False
    mute_remaining_s: Optional[int] = Field(default=None, ge=0, le=30)
    fan_on: bool = False
    red_led_on: bool = False
    green_led_on: bool = False
    buzzer_on: bool = False

    @field_validator("device_id")
    @classmethod
    def normalize_device_id(cls, value: str) -> str:
        return value.strip()


class ThresholdsPayload(BaseModel):
    temperature_high_c: float = Field(ge=-50.0, le=100.0)
    gas_rise_delta: float = Field(ge=0.0, le=200.0)
    door_open_seconds: float = Field(ge=30.0, le=3600.0)
    low_inventory_kg: float = Field(ge=0.0, le=50.0)
    offline_seconds: float = Field(ge=30.0, le=3600.0)


class AlertAckPayload(BaseModel):
    acknowledged_by: str = Field(default="operator", min_length=1, max_length=128)


class RFIDScanPayload(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    uid: str = Field(min_length=4, max_length=32)
    firmware_version: str = Field(default="1.0.0", min_length=1, max_length=32)

    @field_validator("device_id", "uid")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return value.strip()
