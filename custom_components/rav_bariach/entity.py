"""Shared base entity for the Rav Bariach integration.

Every entity of one lock shares the same data dict (the record from
``get-locks``) and refreshes it from three sources: WebSocket pushes for the
device, a coordinator refresh (after a WebSocket reconnect), and the gateway's
connection state, which drives availability so a lost WebSocket does not leave
a stale "locked" on the dashboard.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER, OnlineStatus

_LOGGER = logging.getLogger(__name__)


class RavBariachEntity(Entity):
    """Base class for all entities of one lock."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: dict[str, Any], data: dict[str, Any]) -> None:
        self._session = hub["session"]
        self._gateway = hub["gateway"]
        self._coordinator = hub["coordinator"]
        self._data = data
        self._device_id = str(data.get("deviceId"))
        self.last_update: datetime | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._gateway.register_listener(self._device_id, self._handle_ws_update)
        )
        self.async_on_remove(
            self._gateway.register_connection_listener(self._handle_connection)
        )
        self.async_on_remove(
            self._coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_ws_update(self, payload: dict[str, Any]) -> None:
        if not payload:
            return
        self._data.update(payload)
        self.last_update = dt_util.utcnow()
        self._on_data_update()
        self.async_write_ha_state()

    @callback
    def _handle_connection(self, connected: bool) -> None:
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        locks = getattr(self._coordinator.data, "locks", None) or []
        for lock in locks:
            if str(lock.get("deviceId")) == self._device_id:
                self._data.update(lock)
                self.last_update = dt_util.utcnow()
                self._on_data_update()
                break
        self.async_write_ha_state()

    def _on_data_update(self) -> None:
        """Hook for subclasses; runs before the state is written."""

    def _int(self, key: str) -> int | None:
        try:
            return int(self._data.get(key))
        except (ValueError, TypeError):
            return None

    @property
    def lock_online(self) -> bool:
        return self._int("isOnline") == OnlineStatus.ONLINE

    @property
    def available(self) -> bool:
        return self._gateway.connected and self.lock_online

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._data.get("deviceName", "Rav Bariach Lock"),
            "manufacturer": MANUFACTURER,
            "model": self._data.get("deviceModel"),
            "sw_version": self._data.get("firmwareVersion"),
            "hw_version": self._data.get("hardwareVersion"),
            "suggested_area": self._data.get("deviceName"),
        }
