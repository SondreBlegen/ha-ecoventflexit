import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ecoventv2 import Fan
from .const import DOMAIN, ECOVENT_DEVICES, CONF_FAN_ID

_LOGGER = logging.getLogger(__name__)

# Binary sensor definitions: (attribute_name_on_fan_object, param_id, name, device_class, icon, on_value)
BINARY_SENSOR_TYPES = {
    "filter_replacement": (
        "filter_replacement_status",
        136,
        "Filter Replacement",
        BinarySensorDeviceClass.PROBLEM,
        "mdi:air-filter",
        "on"  # "on" means filter needs replacement
    ),
    "humidity_triggered": (
        "humidity_status",
        772,
        "Humidity Triggered",
        None,
        "mdi:water-alert",
        "on"
    ),
    "relay": (
        "relay_status",
        50,
        "Relay Status",
        None,
        "mdi:electric-switch",
        "on"
    ),
    "analogv": (
        "analogV_status",
        773,
        "Analog Voltage Triggered",
        None,
        "mdi:sine-wave",
        "on"
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ecovent Flexit binary sensor platform."""
    _LOGGER.debug("Setting up Ecovent Flexit binary sensor platform for entry: %s", config_entry.entry_id)

    ecovent_fan_instances = hass.data[DOMAIN][ECOVENT_DEVICES]

    entities = []
    for ecovent_fan_instance in ecovent_fan_instances:
        if ecovent_fan_instance.host == config_entry.data.get('ip_address') and \
           ecovent_fan_instance.id == config_entry.data.get(CONF_FAN_ID):
            for sensor_key, (attr, param_id, name, device_class, icon, on_value) in BINARY_SENSOR_TYPES.items():
                entities.append(EcoventFlexitBinarySensor(
                    ecovent_fan_instance,
                    sensor_key,
                    attr,
                    param_id,
                    name,
                    device_class,
                    icon,
                    on_value
                ))

    if entities:
        async_add_entities(entities, True)


class EcoventFlexitBinarySensor(BinarySensorEntity):
    """Representation of an Ecovent Flexit binary sensor."""

    _attr_has_entity_name = True

    def __init__(self, fan_instance: Fan, sensor_key: str, attr_name: str,
                 param_id: int, name: str, device_class: BinarySensorDeviceClass | None,
                 icon: str | None, on_value: str) -> None:
        """Initialize the binary sensor."""
        self._fan = fan_instance
        self._sensor_key = sensor_key
        self._attr_name = name
        self._attr_unique_id = f"{self._fan.id}_{sensor_key}"
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_is_on = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._fan.name,
            "model": getattr(self._fan, 'unit_type', "Ecovent Flexit Fan"),
            "manufacturer": "Flexit"
        }
        self._attr_should_poll = True
        self._attr_translation_key = sensor_key

        self._attr_name_on_fan = attr_name
        self._param_id = param_id
        self._on_value = on_value

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary sensor is on."""
        return self._attr_is_on

    async def async_update(self) -> None:
        """Fetch new state data for the binary sensor."""
        _LOGGER.debug("Updating binary sensor %s for fan %s", self._attr_name, self._fan.name)
        
        # Try to read from attribute first
        raw_value = getattr(self._fan, self._attr_name_on_fan, None)
        
        if raw_value is not None:
            # Compare string value
            self._attr_is_on = (raw_value == self._on_value)
        else:
            # Fallback: read directly from param
            param_value = self._fan.get_param(self._param_id)
            if param_value is not None:
                self._attr_is_on = (param_value == 1)
            else:
                self._attr_is_on = None
                _LOGGER.debug("Raw value for %s on fan %s was None", self._attr_name_on_fan, self._fan.name)
