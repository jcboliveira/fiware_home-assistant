"""Config flow for FIWARE integration (UI setup)."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from . import DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("api_url", default="https://broker.fiware.urbanplatform.portodigital.pt/v2/entities"): str,
        vol.Optional("scan_interval", default=60): int,
        vol.Optional("stations", default=""): str,
        vol.Optional("exclude", default=""): str,
    }
)


class FiwareConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FIWARE."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        # Normalize blank strings to None
        if user_input.get("stations") == "":
            user_input["stations"] = None
        if user_input.get("exclude") == "":
            user_input["exclude"] = None

        return self.async_create_entry(title="FIWARE", data=user_input)
