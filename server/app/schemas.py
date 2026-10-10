from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ReadingPayload(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    temperature_c: float = Field(ge=-50.0, le=100.0)
    humidity_pct: float = Field(ge=0.0, le=100.0)
    gas_voc: float = Field(ge=0.0, le=5000.0)
    weight_kg: float = Field(ge=0.0, le=200.0)
    door_open: bool = False
    battery_mv: Optional[float] = Field(default=None, ge=0.0, le=50000.0)
    wifi_rssi_dbm: Optional[int] = Field(default=None, ge=-120, le=0)
    firmware_version: str = Field(default="1.0.0", min_length=1, max_length=32)
    uptime_s: Optional[int] = Field(default=None, ge=0)

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
