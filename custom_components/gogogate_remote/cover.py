"""Cover platform for GoGoGate2 Remote integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .api import GogoGate2API
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the GoGoGate2 Remote cover platform."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = entry_data["coordinator"]
    api: GogoGate2API = entry_data["api"]
    info = coordinator.data

    entities = []
    for door_id in [1, 2, 3]:
        door = info.get(f"door{door_id}", {})
        if door.get("name") or door.get("status") not in ("undefined", "", None):
            entities.append(GogoGate2Cover(coordinator, api, door_id, entry))

    async_add_entities(entities)


class GogoGate2Cover(CoordinatorEntity, CoverEntity):
    """Representation of a GoGoGate2 garage door."""

    _attr_device_class = CoverDeviceClass.GARAGE
    _attr_has_entity_name = True
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
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
        door = coordinator.data.get(f"door{door_id}", {})
        device_name = coordinator.data.get("name") or "GoGoGate2"
        uid = entry.unique_id or entry.entry_id

        self._attr_name = door.get("name") or f"Door {door_id}"
        self._attr_unique_id = f"{uid}_door{door_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name=device_name,
            manufacturer="GoGoGate",
            model=coordinator.data.get("model") or "GoGoGate2",
            sw_version=coordinator.data.get("firmware") or None,
        )
        self._attr_is_closed = self._status_to_is_closed(door.get("status"))

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
        if self.is_closed is False:
            _LOGGER.debug("Door %s is already open, ignoring open request", self._door_id)
            return
        try:
            await self.hass.async_add_executor_job(self._api.activate, self._door_id)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to open door %s: %s", self._door_id, err)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the garage door."""
        if self.is_closed is True:
            _LOGGER.debug("Door %s is already closed, ignoring close request", self._door_id)
            return
        try:
            await self.hass.async_add_executor_job(self._api.activate, self._door_id)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to close door %s: %s", self._door_id, err)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        door = self.coordinator.data.get(f"door{self._door_id}", {})
        self._attr_is_closed = self._status_to_is_closed(door.get("status"))
        self.async_write_ha_state()
