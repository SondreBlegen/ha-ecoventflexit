"""Constants for the Ecovent Flexit integration."""

from datetime import timedelta
from homeassistant.const import Platform # Import Platform directly here

DOMAIN = 'ecoventflexit'

# Configuration keys
CONF_FAN_ID = 'fan_id'

# Data storage keys
ECOVENT_DEVICES = 'ecovent_flexit_devices'

# Service definitions
SERVICE_SET_AIRFLOW = "set_airflow"

# Airflow modes from the library's params (as strings)
AIRFLOW_MODES = ["ventilation", "heat_recovery", "air_supply", "something"]

# Default polling interval
SCAN_INTERVAL = timedelta(seconds=10)

# Platforms to be loaded
PLATFORMS = [
    Platform.FAN,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    # Add other platforms here if you introduce them (e.g., climate, number)
]

# Fan speed mappings (for clarity, although FanEntity handles percentages)
FAN_SPEED_LEVELS = {
    0: 'standby',
    1: 'low',
    2: 'medium',
    3: 'high',
    255: 'manual'
}

# Timer Modes for Select entity
TIMER_MODES = {
    0: 'off',
    1: 'night',
    2: 'party'
}