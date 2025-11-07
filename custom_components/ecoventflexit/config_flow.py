import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import (
    CONF_NAME,
    CONF_IP_ADDRESS,
    CONF_PORT,
    CONF_PASSWORD,
)

# Assume ecoventv2 is a local file within the custom component
from ecoventv2 import Fan
from .const import DOMAIN, CONF_FAN_ID

_LOGGER = logging.getLogger(__name__)

class EcoventFlexitConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ecovent Flexit."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            ip_address = user_input[CONF_IP_ADDRESS]
            port = user_input.get(CONF_PORT, 4000)
            fan_id = user_input[CONF_FAN_ID]
            password = user_input[CONF_PASSWORD]
            name = user_input.get(CONF_NAME, f"Ecovent Flexit ({ip_address})")

            # Set unique_id early to check for existing entries
            await self.async_set_unique_id(fan_id)
            self._abort_if_unique_id_configured()

            # Validate if the device can be connected using the provided credentials
            try:
                # Use hass.async_add_executor_job for blocking I/O (from ecoventv2 library)
                await self.hass.async_add_executor_job(
                    self._test_connection, ip_address, port, fan_id, password, name
                )
            except Exception as e:
                _LOGGER.error("Failed to connect to Ecovent Flexit at %s: %s", ip_address, e)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_IP_ADDRESS): str,
                vol.Optional(CONF_PORT, default=4000): vol.Coerce(int),
                vol.Required(CONF_FAN_ID): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_NAME): str,
            }),
            errors=errors,
        )

    def _test_connection(self, ip_address, port, fan_id, password, name):
        """Test if we can connect to the Ecovent Flexit fan (blocking call)."""
        fan = Fan(host=ip_address, password=password, fan_id=fan_id, port=port, name=name)
        fan.update() # Attempt to update to check connection and credentials
        # If no exception, connection is successful
        _LOGGER.debug("Test connection to Ecovent Flexit successful for %s.", fan_id)

    @callback
    def async_get_options_flow(self, config_entry):
        """Get the options flow for this handler."""
        # This integration does not have options for now, so return a no-op handler
        return EcoventFlexitOptionsFlowHandler(config_entry)


class EcoventFlexitOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Ecovent Flexit options."""

    def __init__(self, config_entry):
        """Initialize Ecovent Flexit options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        # For now, no options are managed via the UI, so just show an empty form or return done
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))