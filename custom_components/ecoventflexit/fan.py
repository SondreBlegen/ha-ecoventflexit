import logging
import math

from homeassistant.components.fan import (
    FanEntityFeature,
    FanEntity,
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH,
)
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)
from homeassistant.helpers.event import async_track_time_interval

# Assume ecoventv2 is a local file within the custom component
from ecoventv2 import Fan
from .const import DOMAIN, ECOVENT_DEVICES, SERVICE_SET_AIRFLOW, AIRFLOW_MODES, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Constants for the fan entity
ATTR_AIRFLOW_MODE = "airflow_mode"
ATTR_FAN_ID_EXPOSED = "device_id" # To expose the fan ID as an attribute, differentiate from unique_id

# Ordered list of speeds, excluding 'off' for percentage calculation
# This aligns with Home Assistant's fan percentage helper.
ORDERED_FAN_SPEEDS = [SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]
# Speed range mapping from percentage to the fan's internal integer speed levels (1, 2, 3)
SPEED_RANGE = (1, 3) # Corresponds to low (1), medium (2), high (3) in the fan's protocol

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ecovent Flexit fan platform."""
    _LOGGER.debug("Setting up Ecovent Flexit fan platform for entry: %s", config_entry.entry_id)

    # Retrieve the fan instance(s) stored in hass.data by __init__.py
    ecovent_fan_instances = hass.data[DOMAIN][ECOVENT_DEVICES]

    entities = []
    for ecovent_fan_instance in ecovent_fan_instances:
        # Check if this instance belongs to the current config_entry
        # (This handles cases where multiple entries might call setup or on reload)
        if ecovent_fan_instance.host == config_entry.data.get('ip_address') and \
           ecovent_fan_instance.id == config_entry.data.get(CONF_FAN_ID):
            entities.append(EcoventFlexitFan(ecovent_fan_instance))

    if entities:
        async_add_entities(entities, True) # Add entities, requesting immediate update
    else:
        _LOGGER.warning("No Ecovent Flexit fan instances found for config entry %s", config_entry.entry_id)


class EcoventFlexitFan(FanEntity):
    """Representation of an Ecovent Flexit fan."""

    _attr_has_entity_name = True
    _attr_translation_key = "ecovent_flexit_fan" # For localization
    _attr_icon = "mdi:fan" # Default icon

    def __init__(self, ecovent_fan_instance: Fan) -> None:
        """Initialize the fan."""
        self._fan = ecovent_fan_instance
        self._attr_name = self._fan.name # Use the name passed during init
        self._attr_unique_id = self._fan.id # Use fan ID as unique ID for the entity

        # Initial state will be fetched during async_add_entities with update_before_add=True
        # These will be populated by async_update
        self._current_speed_level = None # Raw integer speed from fan
        self._current_state_bool = None # True/False for on/off
        self._current_airflow_mode = None # String airflow mode from fan

        # Store mappings from the fan library for easy access
        self._states_map = self._fan.params.get(1, [None, {}])[1]
        self._speeds_map = self._fan.params.get(2, [None, {}])[1]
        self._airflows_map = self._fan.params.get(183, [None, {}])[1]
        self._unit_types_map = self._fan.params.get(185, [None, {}])[1]


    @property
    def should_poll(self) -> bool:
        """Return True if entity should be polled for state updates."""
        return True # The ecoventv2 library does not use callbacks, so we must poll

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if self._current_speed_level is None or self._current_speed_level == 0: # 0 is 'standby'
            return 0
        return ranged_value_to_percentage(SPEED_RANGE, self._current_speed_level)

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports (excluding off/standby)."""
        return len(ORDERED_FAN_SPEEDS)

    @property
    def supported_features(self) -> FanEntityFeature:
        """Return supported features."""
        # If you want to use airflow modes as Home Assistant preset modes,
        # add FanEntityFeature.PRESET_MODE. You would also need to implement
        # `preset_mode` and `set_preset_mode`. For simplicity now, just SET_SPEED.
        return FanEntityFeature.SET_SPEED

    @property
    def is_on(self) -> bool | None:
        """Return True if the fan currently is on."""
        return self._current_state_bool

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return device specific state attributes."""
        attrs = {
            ATTR_AIRFLOW_MODE: self._current_airflow_mode,
            ATTR_FAN_ID_EXPOSED: self._fan.id, # Expose the raw device ID
            "ip_address": self._fan.host,
            "port": self._fan.port,
            # Add other attributes that you want to expose, e.g., from fan.update()
            "fan1_speed_rpm": getattr(self._fan, 'fan1_speed', None),
            "fan2_speed_rpm": getattr(self._fan, 'fan2_speed', None),
            "humidity": getattr(self._fan, 'humidity', None),
            "unit_type": getattr(self._fan, 'unit_type', None),
            "battery_voltage": getattr(self._fan, 'battery_voltage', None),
            "firmware": getattr(self._fan, 'firmware', None),
            "filter_timer_countdown": getattr(self._fan, 'filter_timer_countdown', None),
            "machine_hours": getattr(self._fan, 'machine_hours', None),
            "alarm_status": getattr(self._fan, 'alarm_status', None),
        }
        return {k: v for k, v in attrs.items() if v is not None} # Only return non-None attributes

    async def async_update(self) -> None:
        """Get the latest data from the fan and update the entity's state."""
        _LOGGER.debug("Updating state for Ecovent Flexit fan %s (%s)", self.name, self.unique_id)
        try:
            # Run blocking I/O (self._fan.update()) in the event loop executor
            await self.hass.async_add_executor_job(self._fan.update)

            # Update entity's internal state based on the updated _fan object
            self._current_state_bool = self._fan.state == 'on' if self._fan.state else False

            # Map the fan's string speed ('low', 'medium', etc.) to the internal integer level
            # If speed is 'standby' (0) or 'manual' (255), convert to 0 for percentage logic
            if self._fan.speed:
                speed_str_to_int = {v: k for k, v in self._speeds_map.items()}
                self._current_speed_level = speed_str_to_int.get(self._fan.speed, 0)
                if self._current_speed_level == 255: # If manual, treat as its last set speed or a default
                    self._current_speed_level = self._fan.man_speed if getattr(self._fan, 'man_speed', None) else 0 # Assume man_speed holds the manual level
            else:
                self._current_speed_level = 0

            self._current_airflow_mode = self._fan.airflow

            _LOGGER.debug("Fan %s updated: State=%s, Speed Level=%s ('%s'), Airflow=%s",
                          self.name, self._current_state_bool, self._current_speed_level, self._fan.speed, self._current_airflow_mode)

        except Exception as e:
            _LOGGER.error("Error updating state for Ecovent Flexit fan %s (%s): %s", self.name, self.unique_id, e, exc_info=True)
            # Set state to None or unknown if communication fails
            self._current_state_bool = None
            self._current_speed_level = None
            self._current_airflow_mode = None

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        _LOGGER.debug("Setting percentage for %s to %s%%", self.name, percentage)
        if percentage == 0:
            await self.async_turn_off()
            return

        # Convert percentage to the fan's internal speed level (1-3)
        target_speed_level = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        target_speed_level = max(1, min(3, target_speed_level)) # Ensure it's within [1, 3]

        _LOGGER.debug("Mapped percentage %s%% to speed level %s for %s", percentage, target_speed_level, self.name)

        try:
            # Ensure the fan is turned on before setting speed if it's off
            if not self._current_state_bool:
                await self.async_turn_on() # This will set it to default speed if not specified

            # Call the library's set_speed method with the integer level
            await self.hass.async_add_executor_job(self._fan.set_speed, target_speed_level)
            await self.async_update() # Update immediately to reflect the change
        except Exception as e:
            _LOGGER.error("Error setting speed for Ecovent Flexit fan %s: %s", self.name, e, exc_info=True)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None, # Not used for now, but kept for method signature
        **kwargs,
    ) -> None:
        """Turn on the fan."""
        _LOGGER.debug("Turning on Ecovent Flexit fan %s with percentage %s", self.name, percentage)
        try:
            await self.hass.async_add_executor_job(self._fan.set_state_on)
            if percentage is not None:
                await self.async_set_percentage(percentage)
            else:
                # If no percentage specified, set to a default (e.g., low speed, which is 1)
                await self.async_set_percentage(ranged_value_to_percentage(SPEED_RANGE, 1))
            await self.async_update()
        except Exception as e:
            _LOGGER.error("Error turning on Ecovent Flexit fan %s: %s", self.name, e, exc_info=True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the fan."""
        _LOGGER.debug("Turning off Ecovent Flexit fan %s", self.name)
        try:
            await self.hass.async_add_executor_job(self._fan.set_state_off)
            await self.async_update()
        except Exception as e:
            _LOGGER.error("Error turning off Ecovent Flexit fan %s: %s", self.name, e, exc_info=True)

    # Custom method to handle setting airflow, called by the service `ecoventflexit.set_airflow`
    async def set_airflow(self, airflow_int: int) -> None:
        """Set the airflow mode directly using the integer value from the protocol."""
        _LOGGER.debug("Setting airflow for %s to integer %s", self.name, airflow_int)
        try:
            await self.hass.async_add_executor_job(self._fan.set_airflow, airflow_int)
            await self.async_update()
        except Exception as e:
            _LOGGER.error("Error setting airflow for Ecovent Flexit fan %s: %s", self.name, e, exc_info=True)