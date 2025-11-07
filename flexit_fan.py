import logging
import sys

try:
    from ecoventv2 import Fan
except ImportError:
    print("Error: The 'ecovent' library (pyEcovent) is not installed.")
    print("Please install it using: pip install ecovent")
    sys.exit(1)

# Configure basic logging to see potential debug messages from the library
# Set the root logger to DEBUG to catch everything
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
_LOGGER = logging.getLogger(__name__)

# Also, specifically set the 'ecovent' logger to DEBUG if it exists (good practice)
# This might reveal what's happening internally in the library
logging.getLogger('ecovent').setLevel(logging.DEBUG)


# --- Configuration for your Ecovent fan ---
FAN_IP_ADDRESS = "192.168.179.82"  # Your fan's IP
FAN_NAME = "Theodor ventilation"
FAN_PORT = 4000  # Default port from the Home Assistant integration

def read_fan_info():
    """
    Connects to the Ecovent fan and attempts to read its current speed and state.
    """
    _LOGGER.info(f"Attempting to connect to Ecovent fan '{FAN_NAME}' at {FAN_IP_ADDRESS}:{FAN_PORT}")
    try:
        fan = Fan(FAN_IP_ADDRESS, password='11111111', fan_id='002300424B465707')

        _LOGGER.info("Attempting to update fan state...")
        fan.update()

        current_state = fan.state
        current_speed = fan.speed
        current_airflow = fan.airflow

        _LOGGER.info(f"Successfully connected to '{FAN_NAME}' ({FAN_IP_ADDRESS}).")
        _LOGGER.info(f"Fan State: {'On' if current_state else 'Off'}")
        _LOGGER.info(f"Current Fan Speed: {current_speed}")
        _LOGGER.info(f"Current Airflow Mode: {current_airflow}")

        # Optional: Print all available attributes of the fan object to see if anything else is populated
        _LOGGER.debug("Inspecting all fan attributes:")
        for attr_name in dir(fan):
            if not attr_name.startswith('_') and attr_name not in ['update', 'set_state_on', 'set_state_off', 'set_speed', 'set_airflow', 'host', 'name', 'port']:
                try:
                    value = getattr(fan, attr_name)
                    if value is not None: # Only show populated attributes
                        _LOGGER.debug(f"  {attr_name}: {value}")
                except Exception as e:
                    _LOGGER.debug(f"  {attr_name}: (could not retrieve: {e})")


    except Exception as e:
        _LOGGER.error(f"Failed to connect to or read from Ecovent fan: {e}")
        _LOGGER.error("Please ensure the fan's IP address and port are correct,")
        _LOGGER.error("that the 'ecovent' library is compatible with your fan model,")
        _LOGGER.error("and that the fan is reachable on the network.")

if __name__ == "__main__":
    read_fan_info()