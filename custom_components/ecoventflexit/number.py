import logging

from homeassistant.components.number import NumberEntity, NumberDeviceClass, NumberMode
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ecoventv2 import Fan
from .const import DOMAIN, ECOVENT_DEVICES, CONF_FAN_ID

_LOGGER = logging.getLogger(__name__)

# Number definitions: (attribute_name, param_id, name, min, max, step, unit, device_class, icon)
NUMBER_TYPES = {
    "humidity_threshold": (
        "humidity_treshold",  # Note: Typo in library - 'treshold' not 'threshold'
        25,
        "Humidity Threshold",
        0,
        100,
        1,
        PERCENTAGE,
        NumberDeviceClass.HUMIDITY,
        "mdi:water-percent-alert"
    ),
    "analogv_threshold": (
        "analogV_treshold",  # Note: Typo in library - 'treshold' not 'threshold'
        184,
        "Analog Voltage Threshold",
        0,
        100,
        1,
        PERCENTAGE,
        None,
        "mdi:tune"
    ),
    "boost_time": (
        "boost_time",
        102,
        "Boost Time",
        1,
        240,  # Up to 4 hours in minutes
        1,
        UnitOfTime.MINUTES,
        NumberDeviceClass.DURATION,
        "mdi:timer-outline"
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ecovent Flexit number platform."""
    _LOGGER.debug("Setting up Ecovent Flexit number platform for entry: %s", config_entry.entry_id)

    ecovent_fan_instances = hass.data[DOMAIN][ECOVENT_DEVICES]

    entities = []
    for ecovent_fan_instance in ecovent_fan_instances:
        if ecovent_fan_instance.host == config_entry.data.get('ip_address') and \
           ecovent_fan_instance.id == config_entry.data.get(CONF_FAN_ID):
            for number_key, (attr, param_id, name, min_val, max_val, step, unit, device_class, icon) in NUMBER_TYPES.items():
                entities.append(EcoventFlexitNumber(
                    ecovent_fan_instance,
                    number_key,
                    attr,
                    param_id,
                    name,
                    min_val,
                    max_val,
                    step,
                    unit,
                    device_class,
                    icon
                ))

    if entities:
        async_add_entities(entities, True)


class EcoventFlexitNumber(NumberEntity):
    """Representation of an Ecovent Flexit number entity."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(self, fan_instance: Fan, number_key: str, attr_name: str,
                 param_id: int, name: str, min_val: float, max_val: float,
                 step: float, unit: str | None, device_class: NumberDeviceClass | None,
                 icon: str | None) -> None:
        """Initialize the number entity."""
        self._fan = fan_instance
        self._number_key = number_key
        self._attr_name = name
        self._attr_unique_id = f"{self._fan.id}_{number_key}"
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_native_value = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._fan.name,
            "model": getattr(self._fan, 'unit_type', "Ecovent Flexit Fan"),
            "manufacturer": "Flexit"
        }
        self._attr_should_poll = True
        self._attr_translation_key = number_key

        self._attr_name_on_fan = attr_name
        self._param_id = param_id

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        _LOGGER.debug("Setting %s for fan %s to %s", self._attr_name, self._fan.name, value)
        try:
            await self.hass.async_add_executor_job(self._fan.set_param, self._param_id, int(value))
            self._attr_native_value = value
            self.async_write_ha_state()
            await self.async_update()
        except Exception as e:
            _LOGGER.error("Error setting %s for Ecovent Flexit fan %s: %s", self._attr_name, self._fan.name, e, exc_info=True)

    async def async_update(self) -> None:
        """Fetch new state data for the number entity."""
        _LOGGER.debug("Updating number %s for fan %s", self._attr_name, self._fan.name)
        
        # Try to read from attribute first
        raw_value = getattr(self._fan, self._attr_name_on_fan, None)
        
        if raw_value is not None:
            # Parse the value if it's a string with units
            if isinstance(raw_value, str):
                # Extract numeric value from strings like "30 m" or "70"
                try:
                    self._attr_native_value = float(raw_value.split()[0])
                except (ValueError, IndexError):
                    _LOGGER.warning("Could not parse numeric value from %s", raw_value)
                    self._attr_native_value = None
            else:
                self._attr_native_value = float(raw_value)
        else:
            # Fallback: read directly from param
            param_value = self._fan.get_param(self._param_id)
            if param_value is not None:
                self._attr_native_value = float(param_value)
            else:
                self._attr_native_value = None
                _LOGGER.debug("Raw value for %s on fan %s was None", self._attr_name_on_fan, self._fan.name)
