import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ecoventv2 import Fan
from .const import DOMAIN, ECOVENT_DEVICES, CONF_FAN_ID

_LOGGER = logging.getLogger(__name__)

# Switch definitions: (attribute_name_on_fan_object, param_id, name, icon)
SWITCH_TYPES = {
    "heater": ("heater_status", 129, "Heater", "mdi:heating-coil"),
    "boost": ("boost_status", 6, "Boost", "mdi:rocket-launch-outline"),
    "humidity_sensor": ("humidity_sensor_state", 15, "Humidity Sensor Auto", "mdi:water-thermometer"),
    "relay_sensor": ("relay_sensor_state", 20, "Relay Sensor", "mdi:electric-switch"),
    "analogv_sensor": ("analogV_sensor_state", 22, "Analog Voltage Sensor", "mdi:sine-wave"),
    "cloud_server": ("cloud_server_state", 133, "Cloud Server", "mdi:cloud"),
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ecovent Flexit switch platform."""
    _LOGGER.debug("Setting up Ecovent Flexit switch platform for entry: %s", config_entry.entry_id)

    ecovent_fan_instances = hass.data[DOMAIN][ECOVENT_DEVICES]

    entities = []
    for ecovent_fan_instance in ecovent_fan_instances:
        if ecovent_fan_instance.host == config_entry.data.get('ip_address') and \
           ecovent_fan_instance.id == config_entry.data.get(CONF_FAN_ID):
            for switch_key, (attr, param_id, name, icon) in SWITCH_TYPES.items():
                entities.append(EcoventFlexitSwitch(
                    ecovent_fan_instance,
                    switch_key,
                    attr,
                    param_id,
                    name,
                    icon
                ))

    if entities:
        async_add_entities(entities, True)


class EcoventFlexitSwitch(SwitchEntity):
    """Representation of an Ecovent Flexit switch."""

    _attr_has_entity_name = True

    def __init__(self, fan_instance: Fan, switch_key: str, attr_name: str,
                 param_id: int, name: str, icon: str | None) -> None:
        """Initialize the switch."""
        self._fan = fan_instance
        self._switch_key = switch_key
        self._attr_name = name
        self._attr_unique_id = f"{self._fan.id}_{switch_key}"
        self._attr_icon = icon
        self._attr_is_on = None # Will be set by async_update
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._fan.name,
            "model": getattr(self._fan, 'unit_type', "Ecovent Flexit Fan"),
            "manufacturer": "Flexit"
        }
        self._attr_should_poll = True
        self._attr_translation_key = switch_key

        self._attr_name_on_fan = attr_name
        self._param_id = param_id # Parameter ID for set_param

    @property
    def is_on(self) -> bool | None:
        """Return True if the switch is on."""
        return self._attr_is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        _LOGGER.debug("Turning on %s for fan %s", self._attr_name, self._fan.name)
        try:
            # Set param to 1 (which maps to 'on' in the library's internal mapping)
            await self.hass.async_add_executor_job(self._fan.set_param, self._param_id, 1)
            self._attr_is_on = True
            self.async_write_ha_state()
            await self.async_update()
        except Exception as e:
            _LOGGER.error("Error turning on switch %s for Ecovent Flexit fan %s: %s", self._attr_name, self._fan.name, e, exc_info=True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        _LOGGER.debug("Turning off %s for fan %s", self._attr_name, self._fan.name)
        try:
            # Set param to 0 (which maps to 'off')
            await self.hass.async_add_executor_job(self._fan.set_param, self._param_id, 0)
            self._attr_is_on = False
            self.async_write_ha_state()
            await self.async_update()
        except Exception as e:
            _LOGGER.error("Error turning off switch %s for Ecovent Flexit fan %s: %s", self._attr_name, self._fan.name, e, exc_info=True)

    async def async_update(self) -> None:
        """Fetch new state data for the switch."""
        _LOGGER.debug("Updating switch %s for fan %s", self._attr_name, self._fan.name)
        # Assuming the pyEcoventV2 library's _fan.update() populates attributes like `heater_status` as strings ('on'/'off')
        # Or, we fetch it directly if the library doesn't expose it as a direct attribute
        status_value = self._fan.get_param(self._param_id) # Fetch the raw integer value

        # Map integer status (0/1) to boolean (False/True)
        if status_value is not None:
            # Need to get the mapped string value from the library's internal `params`
            # For simplicity, assuming 0=off, 1=on directly for switches
            self._attr_is_on = status_value == 1
        else:
            self._attr_is_on = None
            _LOGGER.debug("Raw status value for %s (param_id %s) on fan %s was None", self._attr_name, self._param_id, self._fan.name)