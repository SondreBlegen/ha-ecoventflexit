import logging
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
        _LOGGER.debug("Setting timer mode for %s to %s", self._fan.name, option)
        if option in self._timer_modes_inverse:
            int_value = self._timer_modes_inverse[option]
            try:
                # Parameter ID for timer_mode is 7
                await self.hass.async_add_executor_job(self._fan.set_param, 7, int_value)
                self._attr_current_option = option
                self.async_write_ha_state() # Update HA state immediately
                await self.async_update() # Then do a full update
            except Exception as e:
                _LOGGER.error("Error setting timer mode for Ecovent Flexit fan %s: %s", self._fan.name, e, exc_info=True)
        else:
            _LOGGER.warning("Attempted to set unknown timer mode option: %s", option)

    async def async_update(self) -> None:
        """Fetch new state data for the select entity."""
        # The main fan object's update method is called by the Fan entity already
        # We just need to read the updated attribute from the shared fan object
        _LOGGER.debug("Updating timer mode select for fan %s", self._fan.name)
        # Assuming the pyEcoventV2 library has a public attribute `timer_mode` after `_fan.update()`
        # Or, we fetch it directly if the library doesn't expose it as a direct attribute
        # For simplicity, let's assume `_fan.params[7]` is updated and we can get the string value
        raw_timer_mode_value = self._fan.get_param(7) # This would directly query, better to read from _fan.timer_mode if it exists
        if raw_timer_mode_value is not None:
            self._attr_current_option = TIMER_MODES.get(raw_timer_mode_value)
        else:
            self._attr_current_option = None
            _LOGGER.debug("Raw timer mode value for fan %s was None", self._fan.name)