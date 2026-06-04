"""Config flow for GoGoGate2 Remote integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("uid"): str,
        vol.Required("username", default="admin"): str,
        vol.Required("password"): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GoGoGate2 Remote."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                description_placeholders={},
            )

        uid = user_input["uid"].strip().lower()
        username = user_input["username"].strip()
        password = user_input["password"]

        host = f"{uid}.my-gogogate.com"

        # Verify credentials by attempting a connection
        try:
            from .api import GogoGate2API

            api = GogoGate2API(host, username, password)
            await self.hass.async_add_executor_job(api.get_info)
        except ConnectionError as err:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors={"base": "cannot_connect"},
                description_placeholders={"error": str(err)},
            )
        except Exception as err:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors={"base": "unknown"},
                description_placeholders={"error": str(err)},
            )

        # Ensure only one instance per UID
        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"GoGoGate2 ({uid})",
            data={
                "uid": uid,
                "host": host,
                "username": username,
                "password": password,
            },
        )
