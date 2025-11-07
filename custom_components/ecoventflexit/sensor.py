import logging
from typing import Callable, Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfElectricPotential,
    UnitOfTime,
    UnitOfTemperature, # Assuming temperature for some sensors in a full implementation
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ecoventv2 import Fan
from .const import DOMAIN, ECOVENT_DEVICES, CONF_FAN_ID

_LOGGER = logging.getLogger(__name__)

# Sensor definitions: (attribute_name_on_fan_object, sensor_name, unit, device_class, state_class, icon, value_lambda)
SENSOR_TYPES = {
    "humidity": (
        "humidity",
        "Humidity",
        PERCENTAGE,
        SensorDeviceClass.HUMIDITY,
        SensorStateClass.MEASUREMENT,
        "mdi:water-percent",
        lambda value: value
    ),
    "fan1_speed": (
        "fan1_speed",
        "Fan 1 Speed",
        REVOLUTIONS_PER_MINUTE,
        None,
        SensorStateClass.MEASUREMENT,
        "mdi:fan",
        lambda value: value
    ),
    "fan2_speed": (
        "fan2_speed",
        "Fan 2 Speed",
        REVOLUTIONS_PER_MINUTE,
        None,
        SensorStateClass.MEASUREMENT,
        "mdi:fan",
        lambda value: value
    ),
    "battery_voltage": (
        "battery_voltage",
        "Battery Voltage",
        UnitOfElectricPotential.MILLIVOLT,
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
        "mdi:battery-voltage",
        lambda value: int(value.split(' ')[0]) if isinstance(value, str) and 'mV' in value else None # "3075 mV" -> 3075
    ),
    "firmware": (
        "firmware",
        "Firmware Version",
        None,
        None,  # No device class for firmware version
        None,
        "mdi:chip",
        lambda value: value
    ),
    "filter_timer_countdown": (
        "filter_timer_countdown",
        "Filter Countdown",
        UnitOfTime.DAYS, # Assuming the library converts to days, or we parse "77d 23h 17m"
        SensorDeviceClass.DURATION,
        SensorStateClass.MEASUREMENT,
        "mdi:filter-menu",
        lambda value: int(value.split('d')[0]) if isinstance(value, str) and 'd' in value else None # "77d 23h 17m" -> 77
    ),
    "machine_hours": (
        "machine_hours",
        "Machine Hours",
        UnitOfTime.HOURS, # Assuming parsing from "219d 8h 57m"
        SensorDeviceClass.DURATION,
        SensorStateClass.TOTAL_INCREASING, # Total, increasing over time
        "mdi:hours-24",
        lambda value: sum(int(x.strip('hmsd')) for x in value.split() if x[-1] in 'hmsd') # Simple sum for demonstration, needs better parsing
    ),
    "alarm_status": (
        "alarm_status",
        "Alarm Status",
        None,
        None,
        None,
        "mdi:bell-alert",
        lambda value: value
    ),
    "unit_type": (
        "unit_type",
        "Unit Type",
        None,
        None,
        None,
        "mdi:air-filter",
        lambda value: value
    ),
    "current_wifi_ip": (
        "curent_wifi_ip", # Note: corrected typo from `curent_wifi_ip` to `current_wifi_ip` in `pyEcoventV2` if needed, otherwise use `curent_wifi_ip`
        "Current WiFi IP",
        None,
        None, # SensorDeviceClass.IP_ADDRESS could be a thing, but not standard
        None,
        "mdi:ip-network",
        lambda value: value
    ),
    # Add other sensors as desired, e.g., temperatures if exposed by the library
    # "inlet_temperature": ("inlet_temp", "Inlet Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "mdi:thermometer", lambda value: value),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ecovent Flexit sensor platform."""
    _LOGGER.debug("Setting up Ecovent Flexit sensor platform for entry: %s", config_entry.entry_id)

    ecovent_fan_instances = hass.data[DOMAIN][ECOVENT_DEVICES]

    entities = []
    for ecovent_fan_instance in ecovent_fan_instances:
        if ecovent_fan_instance.host == config_entry.data.get('ip_address') and \
           ecovent_fan_instance.id == config_entry.data.get(CONF_FAN_ID):
            for sensor_key, (attr, name, unit, device_class, state_class, icon, value_lambda) in SENSOR_TYPES.items():
                entities.append(EcoventFlexitSensor(
                    ecovent_fan_instance,
                    sensor_key,
                    attr,
                    name,
                    unit,
                    device_class,
                    state_class,
                    icon,
                    value_lambda
                ))

    if entities:
        async_add_entities(entities, True)


class EcoventFlexitSensor(SensorEntity):
    """Representation of an Ecovent Flexit sensor."""

    _attr_has_entity_name = True

    def __init__(self, fan_instance: Fan, sensor_key: str, attr_name: str, name: str,
                 unit: str | None, device_class: SensorDeviceClass | None,
                 state_class: SensorStateClass | None, icon: str | None,
                 value_lambda: Callable[[Any], Any]) -> None:
        """Initialize the sensor."""
        self._fan = fan_instance
        self._sensor_key = sensor_key # For unique ID generation
        self._attr_name = name
        self._attr_unique_id = f"{self._fan.id}_{sensor_key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_icon = icon
        self._attr_native_value = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self._fan.name,
            "model": getattr(self._fan, 'unit_type', "Ecovent Flexit Fan"),
            "manufacturer": "Flexit" # Or "Vents", "Blauberg" depending on your actual device
        }
        self._attr_should_poll = True # Sensors need polling if library doesn't push
        self._attr_translation_key = sensor_key
        self._attr_force_update = True # Important for some sensors to always update

        # Store attribute name and conversion lambda
        self._attr_name_on_fan = attr_name
        self._value_lambda = value_lambda

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        # The main fan object's update method is called by the Fan entity already
        # We just need to read the updated attribute from the shared fan object
        _LOGGER.debug("Updating sensor %s for fan %s", self._attr_name, self._fan.name)
        raw_value = getattr(self._fan, self._attr_name_on_fan, None)
        if raw_value is not None:
            self._attr_native_value = self._value_lambda(raw_value)
        else:
            self._attr_native_value = None
            _LOGGER.debug("Raw value for %s on fan %s was None", self._attr_name_on_fan, self._fan.name)