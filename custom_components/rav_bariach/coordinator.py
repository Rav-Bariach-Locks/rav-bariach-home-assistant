"""Data Update Coordinator."""

import logging
import time
from types import SimpleNamespace

import async_timeout

from homeassistant.config_entries import ConfigEntryDisabler
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, FULLFILMENT_API_URI

_LOGGER = logging.getLogger(__name__)

# get-locks is limited to 15 calls a day, so a reconnect refresh is allowed at
# most once an hour; a flapping link must not burn the whole quota.
RECONNECT_REFRESH_MIN_SECONDS = 3600


class RavBariachDataUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, session, entry):
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=None
        )
        self.session = session
        self.entry = entry
        self._last_reconnect_refresh = 0.0

    async def async_refresh_after_reconnect(self) -> None:
        """Re-read the locks after a WebSocket reconnect, rate-limited."""
        now = time.monotonic()
        if now - self._last_reconnect_refresh < RECONNECT_REFRESH_MIN_SECONDS:
            _LOGGER.debug("Skipping reconnect refresh (rate guard)")
            return
        self._last_reconnect_refresh = now
        await self.async_request_refresh()

    async def _fetch_endpoint_data(self, endpoint: str, data_key: str) -> list:
        try:
            response = await self.session.async_request(
                "POST", f"{FULLFILMENT_API_URI}/{endpoint}"
            )
            if response.status == 429:
                _LOGGER.warning(
                    "Rate limit hit! Disabling integration. The API that retrieves devices "
                    "can be called a maximum of 15 times per day. To prevent server load, "
                    "further requests are stopped."
                )
                self.entry.disabled_by = ConfigEntryDisabler.USER
                raise UpdateFailed(
                        translation_domain=DOMAIN,
                        translation_key="rate_limit_exceeded"
                    )

            response.raise_for_status()
            json_data = await response.json()
            return json_data.get("data", {}).get(data_key, [])

        except UpdateFailed:
            raise
        except Exception as e:

            _LOGGER.warning(f"Failed to retrieve {data_key} data, skipping: {e}")
            return []

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(15):
                locks_data = await self._fetch_endpoint_data("get-locks", "locks")
                if not locks_data and self.data is not None:
                    # A failed re-read must not wipe the entities' data.
                    raise UpdateFailed("get-locks returned no locks")

                return SimpleNamespace(
                    locks=locks_data
                )

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"General error: {err}")
