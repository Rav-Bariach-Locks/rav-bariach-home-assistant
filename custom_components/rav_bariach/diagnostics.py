"""Diagnostics for the Rav Bariach integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {"token", "access_token", "refresh_token", "id_token", "user_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    hub = hass.data[DOMAIN][entry.entry_id]
    gateway = hub["gateway"]
    coordinator = hub["coordinator"]
    last = gateway.last_message_at
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "gateway": {
            "connected": gateway.connected,
            "connect_count": gateway.connect_count,
            "last_message_at": datetime.fromtimestamp(last, timezone.utc).isoformat() if last else None,
        },
        "locks": getattr(coordinator.data, "locks", None),
    }
