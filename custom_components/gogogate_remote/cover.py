"""Cover platform for GoGoGate2 Remote integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import GogoGate2API
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 30


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the GoGoGate2 Remote cover platform."""
    data = entry.data

    api = GogoGate2API(data["host"], data["username"], data["password"])

    async def async_update():
        """Fetch data from the API."""
        try:
            return await hass.async_add_executor_job(api.get_info)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with GoGoGate2: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=async_update,
        update_interval=timedelta(seconds=SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    entities = []
    info = coordinator.data

    for door_id in [1, 2, 3]:
        door = info.get(f"door{door_id}", {})
        if door.get("name"):
            entities.append(GogoGate2Cover(coordinator, api, door_id, entry))
        elif door.get("status") not in ("undefined", ""):
            entities.append(GogoGate2Cover(coordinator, api, door_id, entry))

    async_add_entities(entities)


class GogoGate2Cover(CoordinatorEntity, CoverEntity):
    """Representation of a GoGoGate2 garage door."""

    _attr_device_class = CoverDeviceClass.GARAGE
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: GogoGate2API,
        door_id: int,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._door_id = door_id
        self._entry_id = entry.entry_id
        door = coordinator.data.get(f"door{door_id}", {})
        name = door.get("name", f"Door {door_id}")
        device_name = coordinator.data.get("name", "GoGoGate2")
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_door{door_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": device_name,
            "manufacturer": "GoGoGate",
            "model": coordinator.data.get("model", "GGG2"),
            "sw_version": coordinator.data.get("firmware"),
        }
        self._attr_is_closed = self._status_to_is_closed(
            door.get("status")
        )

    @staticmethod
    def _status_to_is_closed(status: str | None) -> bool | None:
        if status == "closed":
            return True
        if status == "opened":
            return False
        return None

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self.coordinator.last_update_success

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the garage door."""
        try:
            await self.hass.async_add_executor_job(
                self._api.activate, self._door_id
            )
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to open door %s: %s", self._door_id, err)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the garage door."""
        try:
            await self.hass.async_add_executor_job(
                self._api.activate, self._door_id
            )
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to close door %s: %s", self._door_id, err)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the garage door."""
        try:
            await self.hass.async_add_executor_job(
                self._api.activate, self._door_id
            )
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to stop door %s: %s", self._door_id, err)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        door = self.coordinator.data.get(f"door{self._door_id}", {})
        self._attr_is_closed = self._status_to_is_closed(door.get("status"))
        self.async_write_ha_state()
