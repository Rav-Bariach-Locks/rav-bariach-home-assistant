"""Handle Lock operations."""

import json
import logging

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry, ConfigEntryDisabler
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FULLFILMENT_API_URI, LockIsJammed, LockStatus
from .entity import RavBariachEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rav Bariach Lock entities from a config entry."""
    hub = hass.data[DOMAIN][entry.entry_id]
    devices = hub["coordinator"].data.locks

    async_add_entities(RavBariachLock(hub, device_data, entry) for device_data in devices)


class RavBariachLock(RavBariachEntity, LockEntity):

    _attr_name = None

    def __init__(self, hub, data, entry):
        """Initializing properties."""
        super().__init__(hub, data)
        self._attr_unique_id = f"rav_bariach_lock_{self._device_id}"
        self._is_locking = False
        self._is_unlocking = False
        self.entry = entry

    def _on_data_update(self) -> None:
        self._is_locking = False
        self._is_unlocking = False

    @property
    def code_format(self) -> str | None:
        """Return the required code format."""
        if self.is_locked:
            return r"^\d*$"
        return None

    @property
    def is_locking(self) -> bool:
        """Return True if the lock is currently locking."""
        return self._is_locking

    @property
    def is_unlocking(self) -> bool:
        """Return True if the lock is currently unlocking."""
        return self._is_unlocking

    @property
    def is_locked(self) -> bool | None:
        """Return true if lock is locked."""
        val = self._int("status")
        return None if val is None else val == LockStatus.LOCKED

    @property
    def is_jammed(self) -> bool | None:
        """Return True if the lock is jammed."""
        val = self._int("isJammed")
        return None if val is None else val == LockIsJammed.JAMMED

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return {
            "battery_level": self._data.get("batteryLevel"),
            "online": self.lock_online,
            "firmware_version": self._data.get("firmwareVersion"),
            "device_version": self._data.get("deviceVersion"),
            "device_model": self._data.get("deviceModel"),
            "last_update": self.last_update.isoformat() if self.last_update else None,
        }

    async def _send_command(self, operation_type, code):
        """Send command to the API."""
        url = f"{FULLFILMENT_API_URI}/lock-unlock-command"

        try:
            await self._session.async_ensure_token_valid()
        except Exception as err:
            if getattr(err, "status", None) == 429:
                _LOGGER.warning("Token refresh rate limit hit. Retrying later.")
                self.entry.disabled_by = ConfigEntryDisabler.USER
                raise ConfigEntryNotReady(
                    translation_domain=DOMAIN,
                    translation_key="exceptions.rate_limit_exceeded"
                ) from err

            raise

        payload = {
            "smartLockId": self._device_id,
            "smartLockOperation": operation_type,
            "smartLockCode": str(code) if code else "",
        }

        resp = await self._session.async_request("POST", url, json=payload)

        if resp.status >= 400:
            error_body = await resp.text()
            msg_text = error_body
            try:
                if error_body:
                    err_json = json.loads(error_body)
                    if isinstance(err_json, dict) and "message" in err_json:
                        msg_text = err_json["message"]
            except ValueError:
                pass

            _LOGGER.warning("Server Message -> %s", msg_text)
            self._is_locking = False
            self._is_unlocking = False
            self.async_write_ha_state()

            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"server_msg": msg_text},
            )

    async def async_lock(self, **kwargs):
        """Send lock command."""
        code = kwargs.get("code")
        self._is_locking = True
        self._is_unlocking = False
        self.async_write_ha_state()

        try:
            await self._send_command("LOCK", code)
        except Exception:
            self._is_locking = False
            self.async_write_ha_state()
            raise

    async def async_unlock(self, **kwargs):
        """Send unlock command."""
        code = kwargs.get("code")
        if not code:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="code_required"
            )

        self._is_locking = False
        self._is_unlocking = True
        self.async_write_ha_state()

        try:
            await self._send_command("UNLOCK", code)
        except Exception:
            self._is_unlocking = False
            self.async_write_ha_state()
            raise
