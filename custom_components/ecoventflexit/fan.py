import logging
import math

from homeassistant.components.fan import (
    FanEntityFeature,
    FanEntity,
)
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)
# from homeassistant.helpers.event import async_track_time_interval # Not directly used in FanEntity

from ecoventv2 import Fan
from .const import DOMAIN, ECOVENT_DEVICES, CONF_FAN_ID, FAN_SPEED_LEVELS

_LOGGER = logging.getLogger(__name__)

# Constants for the fan entity
ATTR_AIRFLOW_MODE = "airflow_mode"
ATTR_FAN_ID_EXPOSED = "device_id"

# Ordered list of speeds for percentage calculation (matching keys in FAN_SPEED_LEVELS for 'low', 'medium', 'high')
ORDERED_FAN_SPEEDS = [FAN_SPEED_LEVELS[1], FAN_SPEED_LEVELS[2], FAN_SPEED_LEVELS[3]]
SPEED_RANGE = (1, 3) # Corresponds to low (1), medium (2), high (3) in the fan's protocol

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ecovent Flexit fan platform."""
    _LOGGER.debug("Setting up Ecovent Flexit fan platform for entry: %s", config_entry.entry_id)

    ecovent_fan_instances = hass.data[DOMAIN][ECOVENT_DEVICES]

    entities = []
    for ecovent_fan_instance in ecovent_fan_instances:
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
    _attr_translation_key = "ecovent_flexit_fan"
    _attr_icon = "mdi:fan"

    def __init__(self, ecovent_fan_instance: Fan) -> None:
        """Initialize the fan."""
        self._fan = ecovent_fan_instance
        self._attr_name = self._fan.name
        self._attr_unique_id = self._fan.id # Crucial for entity visibility and uniqueness

        self._current_speed_level = None
        self._current_state_bool = None
        self._current_airflow_mode = None

        self._states_map = self._fan.params.get(1, [None, {}])[1]
        self._speeds_map = self._fan.params.get(2, [None, {}])[1]
        self._airflows_map = self._fan.params.get(183, [None, {}])[1]
        self._unit_types_map = self._fan.params.get(185, [None, {}])[1]


    @property
    def should_poll(self) -> bool:
        """Return True if entity should be polled for state updates."""
        return True

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if self._current_speed_level is None or self._current_speed_level == 0:
            return 0
        return ranged_value_to_percentage(SPEED_RANGE, self._current_speed_level)

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports (excluding off/standby)."""
        return len(ORDERED_FAN_SPEEDS)

    @property
    def supported_features(self) -> FanEntityFeature:
        """Return supported features."""
        # You could also add FanEntityFeature.PRESET_MODE if you want to use airflow as presets
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
            ATTR_FAN_ID_EXPOSED: self._fan.id,
            "ip_address": self._fan.host,
            "port": self._fan.port,
        }
        return {k: v for k, v in attrs.items() if v is not None}

    async def async_update(self) -> None:
        """Get the latest data from the fan and update the entity's state."""
        _LOGGER.debug("Updating state for Ecovent Flexit fan %s (%s)", self.name, self.unique_id)
        try:
            await self.hass.async_add_executor_job(self._fan.update)

            self._current_state_bool = self._fan.state == 'on' if self._fan.state else False

            if self._fan.speed:
                speed_str_to_int = {v: k for k, v in self._speeds_map.items()}
                self._current_speed_level = speed_str_to_int.get(self._fan.speed, 0)
                if self._current_speed_level == 255:
                    self._current_speed_level = self._fan.man_speed if getattr(self._fan, 'man_speed', None) else 0
            else:
                self._current_speed_level = 0

            self._current_airflow_mode = self._fan.airflow

            _LOGGER.debug("Fan %s updated: State=%s, Speed Level=%s ('%s'), Airflow=%s",
                          self.name, self._current_state_bool, self._current_speed_level, self._fan.speed, self._current_airflow_mode)

        except Exception as e:
            _LOGGER.error("Error updating state for Ecovent Flexit fan %s (%s): %s", self.name, self.unique_id, e, exc_info=True)
            self._current_state_bool = None
            self._current_speed_level = None
            self._current_airflow_mode = None

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        _LOGGER.debug("Setting percentage for %s to %s%%", self.name, percentage)
        if percentage == 0:
            await self.async_turn_off()
            return

        target_speed_level = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        target_speed_level = max(1, min(3, target_speed_level))

        _LOGGER.debug("Mapped percentage %s%% to speed level %s for %s", percentage, target_speed_level, self.name)

        try:
            if not self._current_state_bool:
                await self.async_turn_on()

            await self.hass.async_add_executor_job(self._fan.set_speed, target_speed_level)
            await self.async_update()
        except Exception as e:
            _LOGGER.error("Error setting speed for Ecovent Flexit fan %s: %s", self.name, e, exc_info=True)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn on the fan."""
        _LOGGER.debug("Turning on Ecovent Flexit fan %s with percentage %s", self.name, percentage)
        try:
            await self.hass.async_add_executor_job(self._fan.set_state_on)
            if percentage is not None:
                await self.async_set_percentage(percentage)
            else:
                await self.async_set_percentage(ranged_value_to_percentage(SPEED_RANGE, 1)) # Default to low
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

    async def set_airflow(self, airflow_int: int) -> None:
        """Set the airflow mode directly using the integer value from the protocol."""
        _LOGGER.debug("Setting airflow for %s to integer %s", self.name, airflow_int)
        try:
            await self.hass.async_add_executor_job(self._fan.set_airflow, airflow_int)
            await self.async_update()
        except Exception as e:
            _LOGGER.error("Error setting airflow for Ecovent Flexit fan %s: %s", self.name, e, exc_info=True)