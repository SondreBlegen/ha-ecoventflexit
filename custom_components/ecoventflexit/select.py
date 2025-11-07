import logging
import asyncio
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ecoventv2 import Fan
from .const import DOMAIN, ECOVENT_DEVICES, CONF_FAN_ID, TIMER_MODES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ecovent Flexit select platform."""
    _LOGGER.debug("Setting up Ecovent Flexit select platform for entry: %s", config_entry.entry_id)

    ecovent_fan_instances = hass.data[DOMAIN][ECOVENT_DEVICES]

    entities = []
    for ecovent_fan_instance in ecovent_fan_instances:
        if ecovent_fan_instance.host == config_entry.data.get('ip_address') and \
           ecovent_fan_instance.id == config_entry.data.get(CONF_FAN_ID):
            entities.append(EcoventFlexitTimerModeSelect(ecovent_fan_instance))

    if entities:
        async_add_entities(entities, True)


class EcoventFlexitTimerModeSelect(SelectEntity):
    """Representation of an Ecovent Flexit Timer Mode select entity."""

    _attr_has_entity_name = True
    _attr_translation_key = "timer_mode"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, fan_instance: Fan) -> None:
        """Initialize the select entity."""
        self._fan = fan_instance
        self._attr_name = "Timer Mode" # Display name
        self._attr_unique_id = f"{self._fan.id}_timer_mode"
        self._attr_options = list(TIMER_MODES.values()) # 'off', 'night', 'party'
        self._attr_current_option = None # Will be set by async_update

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._fan.name,
            "model": getattr(self._fan, 'unit_type', "Ecovent Flexit Fan"),
            "manufacturer": "Flexit"
        }
        self._attr_should_poll = True

        # Store inverse map for setting
        self._timer_modes_inverse = {v: k for k, v in TIMER_MODES.items()}

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return self._attr_current_option

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.info("Setting timer mode for %s to %s", self._fan.name, option)
        if option in self._attr_options:
            try:
                # set_param expects parameter NAME (string) and VALUE (string), not numeric IDs!
                await self.hass.async_add_executor_job(self._fan.set_param, 'timer_mode', option)
                _LOGGER.info("Successfully sent timer mode command")
                self._attr_current_option = option
                self.async_write_ha_state()
            except Exception as e:
                _LOGGER.error("Error setting timer mode for Ecovent Flexit fan %s: %s", self._fan.name, e, exc_info=True)
        else:
            _LOGGER.warning("Attempted to set unknown timer mode option: %s", option)

    async def async_update(self) -> None:
        """Fetch new state data for the select entity."""
        _LOGGER.debug("Updating timer mode select for fan %s", self._fan.name)
        
        # Try to read from timer_mode attribute first (it's a string like "off", "night", "party")
        timer_mode_str = getattr(self._fan, 'timer_mode', None)
        
        if timer_mode_str is not None and timer_mode_str in self._attr_options:
            # The attribute already gives us the string value
            self._attr_current_option = timer_mode_str
        else:
            # Fallback: read from param and convert integer to string
            raw_timer_mode_value = self._fan.get_param(7)
            if raw_timer_mode_value is not None:
                self._attr_current_option = TIMER_MODES.get(raw_timer_mode_value)
            else:
                self._attr_current_option = None
                _LOGGER.debug("Raw timer mode value for fan %s was None", self._fan.name)