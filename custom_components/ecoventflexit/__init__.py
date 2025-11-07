import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import (
    CONF_NAME,
    CONF_IP_ADDRESS,
    CONF_PORT,
    CONF_PASSWORD,
    Platform,
)

# Assume ecoventv2 is a local file within the custom component
from ecoventv2 import Fan
from .const import DOMAIN, ECOVENT_DEVICES, CONF_FAN_ID, SERVICE_SET_AIRFLOW, AIRFLOW_MODES

_LOGGER = logging.getLogger(__name__)

# Service Schema for `ecoventflexit.set_airflow`
SET_AIRFLOW_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("airflow_mode"): vol.In(AIRFLOW_MODES)
    }
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ecovent Flexit from a config entry."""
    _LOGGER.debug("Setting up Ecovent Flexit from config entry: %s", entry.data)

    # Store a domain-specific dictionary in hass.data if it doesn't exist
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Get configuration from config entry
    ip_address = entry.data[CONF_IP_ADDRESS]
    port = entry.data.get(CONF_PORT, 4000)
    fan_id = entry.data[CONF_FAN_ID]
    password = entry.data[CONF_PASSWORD]
    name = entry.data.get(CONF_NAME, f"Ecovent Flexit ({ip_address})")

    try:
        # Initialize the Fan object from your ecoventv2 library
        _LOGGER.info("Initializing Ecovent Flexit fan: %s at %s:%s", name, ip_address, port)
        ecovent_fan_instance = Fan(
            host=ip_address,
            password=password,
            fan_id=fan_id,
            port=port,
            name=name # Pass the friendly name
        )
        # We need to make sure it's connected and updated at least once to populate internal state
        await hass.async_add_executor_job(ecovent_fan_instance.update)
        _LOGGER.info("Ecovent Flexit fan initialized successfully.")

    except Exception as e:
        _LOGGER.error("Failed to connect to Ecovent Flexit fan %s at %s:%s: %s", name, ip_address, port, e)
        return False # Failed to set up

    # Store the device instance in hass.data for the platform to access
    # Using a list, as potentially multiple fans could be configured
    if ECOVENT_DEVICES not in hass.data[DOMAIN]:
        hass.data[DOMAIN][ECOVENT_DEVICES] = []
    hass.data[DOMAIN][ECOVENT_DEVICES].append(ecovent_fan_instance)

    # Forward the setup to the fan platform (fan.py)
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.FAN])

    # Register the custom service `ecoventflexit.set_airflow`
    async def async_set_airflow_service(call):
        """Handle the fan set airflow service."""
        entity_id = call.data.get("entity_id")
        airflow_mode = call.data.get("airflow_mode")

        # Find the fan entity by entity_id
        # This iterates through our stored fan instances
        for ecovent_fan_object in hass.data[DOMAIN].get(ECOVENT_DEVICES, []):
            # The FanEntity will use the fan_id as its unique_id, so compare to that
            if ecovent_fan_object.id == entity_id.split('.')[-1]: # e.g., fan.002300424B465707
                # Get the integer value for the airflow_mode from the fan's protocol mapping
                airflow_int_map = ecovent_fan_object.params.get(183, [None, {}])[1] # 183 is the ID for airflow
                int_airflow_value = next((k for k, v in airflow_int_map.items() if v == airflow_mode), None)

                if int_airflow_value is not None:
                    _LOGGER.debug("Calling set_airflow on %s with mode %s (int: %s)", entity_id, airflow_mode, int_airflow_value)
                    # Use async_add_executor_job for blocking I/O (from ecoventv2 library)
                    await hass.async_add_executor_job(ecovent_fan_object.set_airflow, int_airflow_value)
                else:
                    _LOGGER.warning("Unknown airflow mode '%s' for fan %s", airflow_mode, entity_id)
                return # Service call handled

        _LOGGER.warning("Ecovent Flexit fan entity '%s' not found for set_airflow service.", entity_id)

    hass.services.async_register(
        DOMAIN, SERVICE_SET_AIRFLOW, async_set_airflow_service, schema=SET_AIRFLOW_SCHEMA
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Ecovent Flexit config entry: %s", entry.entry_id)

    # Unload the fan platform first
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, [Platform.FAN])

    if unload_ok:
        # Clean up the stored device instance(s)
        if DOMAIN in hass.data and ECOVENT_DEVICES in hass.data[DOMAIN]:
            fan_id_to_remove = entry.data[CONF_FAN_ID]
            hass.data[DOMAIN][ECOVENT_DEVICES] = [
                device for device in hass.data[DOMAIN][ECOVENT_DEVICES]
                if device.id != fan_id_to_remove
            ]
            if not hass.data[DOMAIN][ECOVENT_DEVICES]:
                hass.data[DOMAIN].pop(ECOVENT_DEVICES) # Remove list if empty

        # If no more devices are configured for this integration, unregister the service
        if not hass.data.get(DOMAIN, {}).get(ECOVENT_DEVICES):
             if hass.services.has_service(DOMAIN, SERVICE_SET_AIRFLOW):
                 hass.services.async_remove(DOMAIN, SERVICE_SET_AIRFLOW)
             if not hass.data.get(DOMAIN):
                 hass.data.pop(DOMAIN, None) # Remove the main domain entry if nothing left

    return unload_ok