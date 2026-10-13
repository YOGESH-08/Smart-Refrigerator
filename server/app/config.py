import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SMART_FRIDGE_SECRET_KEY", "dev-secret-key")
    API_KEY = os.getenv("SMART_FRIDGE_API_KEY", "smart-fridge-demo-key")
    DATABASE_PATH = os.getenv("SMART_FRIDGE_DB_PATH", str(BASE_DIR / "data" / "smart_fridge.db"))
    DEBUG = os.getenv("SMART_FRIDGE_DEBUG", "false").lower() == "true"
    RETENTION_DAYS = int(os.getenv("SMART_FRIDGE_RETENTION_DAYS", "7"))
    DEFAULT_THRESHOLDS = {
        "temperature_high_c": 29.0,
        "gas_rise_delta": 10.0,
        "door_open_seconds": 180.0,
        "low_inventory_kg": 2.5,
        "offline_seconds": 90.0,
    }

    BASELINE_GAS = float(os.getenv("SMART_FRIDGE_BASELINE_GAS", "120.0"))


def get_config() -> Config:
    return Config
