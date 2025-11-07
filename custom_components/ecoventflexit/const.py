"""Constants for the Ecovent Flexit integration."""

from datetime import timedelta

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