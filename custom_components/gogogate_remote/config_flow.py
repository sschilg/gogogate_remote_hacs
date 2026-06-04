"""Config flow for GoGoGate2 Remote integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .api import GogoGate2API
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("uid", description={"suggested_value": "YOUR_UID"}): str,
        vol.Required("username", description={"suggested_value": "admin"}): str,
        vol.Required("password", description={"suggested_value": "YOUR_PASSWORD"}): str,
    }
)


async def _test_connection(
    hass: HomeAssistant, host: str, username: str, password: str
) -> dict[str, Any]:
    """Test the API connection and return device info."""
    api = GogoGate2API(host, username, password)
    try:
        info = await hass.async_add_executor_job(api.get_info)
        _LOGGER.debug("Got info from device: %s", info)
    except Exception as err:
        _LOGGER.error("Connection to %s failed: %s", host, err, exc_info=True)
        raise ConnectionError(str(err)) from err

    # Check that we got a valid response with expected fields
    if not info.get("model"):
        _LOGGER.error("Response missing device model, got keys: %s", list(info.keys()))
        raise ConnectionError("Response missing device model — check your UID is correct")

    # Check for credential errors (API returns <error> in XML)
    if "error" in info:
        _LOGGER.error("API returned error: %s", info["error"])
        raise ConnectionError(f"API error: {info['error']}")

    return info


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GoGoGate2 Remote."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            uid = user_input["uid"].strip().lower()
            username = user_input["username"].strip()
            password = user_input["password"].strip()

            host = f"{uid}.my-gogogate.com"
            _LOGGER.info("Testing connection to %s for user %s", host, username)

            try:
                info = await _test_connection(self.hass, host, username, password)
            except ConnectionError as exc:
                msg = str(exc)
                _LOGGER.error("Cannot connect to %s: %s", host, msg)
                if "credential" in msg.lower() or "password" in msg.lower():
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"

            if not errors:
                # Build a nice title from the device info
                device_name = info.get("name", "GoGoGate2")
                doors = [
                    info.get(f"door{i}", {}).get("name", f"Door {i}")
                    for i in [1, 2, 3]
                    if info.get(f"door{i}", {}).get("name")
                ]
                door_count = len(doors)
                title = f"{device_name} ({door_count} door{'s' if door_count != 1 else ''})"

                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=title,
                    data={
                        "uid": uid,
                        "host": host,
                        "username": username,
                        "password": password,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
