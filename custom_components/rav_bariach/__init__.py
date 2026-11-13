"""The Rav Bariach Integration."""

from __future__ import annotations

import asyncio
import logging
import time

import aiohttp
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import ConfigEntryAuthFailed

from .config_flow import RavBariachOauth2Implementation
from .const import (
    AUTH_URI,
    DISCONNECT_MAX_ATTEMPTS,
    DISCONNECT_RETRY_DELAY,
    DISCONNECT_TIMEOUT,
    DOMAIN,
    FULLFILMENT_API_URI,
    PLATFORMS,
    PUBLIC_ID,
    TOKEN_REFRESH_MARGIN,
    TOKEN_URI,
)
from .coordinator import RavBariachDataUpdateCoordinator
from .gateway import RavBariachGateway

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """OAuth provider implementation."""

    implementation = RavBariachOauth2Implementation(
        hass,
        DOMAIN,
        PUBLIC_ID,
        AUTH_URI,
        TOKEN_URI,
    )

    config_entry_oauth2_flow.async_register_implementation(
        hass,
        DOMAIN,
        implementation,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    try:
        implementation = (
            await config_entry_oauth2_flow.async_get_config_entry_implementation(
                hass, entry
            )
        )
    except Exception as e:
        _LOGGER.warning("Implementation not ready yet, will retry: %s", e)
        raise ConfigEntryNotReady from e

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    coordinator = RavBariachDataUpdateCoordinator(hass, session, entry)

    try:
        await session.async_ensure_token_valid()
    except aiohttp.ClientResponseError as err:
        if err.status == 401 :
            _LOGGER.error(
                "Authentication failed. Please re-authenticate the integration."
            )
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err
        elif err.status == 429:
            _LOGGER.warning("Token refresh rate limit hit. Retrying later.")
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="rate_limit_exceeded",
            ) from err
        else:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="unexpected_error",
            ) from err

    except Exception as err:
        _LOGGER.error("Unexpected error ensuring token valid: %s", err)
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="unexpected_error",
        ) from err
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Initial refresh failed: %s", err)
        raise ConfigEntryNotReady(f"Could not connect to API: {err}")

    try:
        _LOGGER.debug("Initializing Gateway class...")
        gateway = RavBariachGateway(hass, session, entry)
        gateway.on_reconnect = coordinator.async_refresh_after_reconnect

        hass.data[DOMAIN][entry.entry_id] = {
            "session": session,
            "gateway": gateway,
            "coordinator": coordinator,
        }

        entry.async_create_background_task(hass, gateway.start_listen(), "rav_bariach_ws_loop")

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True

    except Exception as e:
        _LOGGER.exception("Unexpected error occurred during setup: %s", e)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)

    if data:
        gateway = data.get("gateway")
        if gateway:
            _LOGGER.debug("Disconnecting Gateway...")
            await gateway.async_disconnect()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Entry data removed from memory.")

    return unload_ok


async def _try_disconnect(
    http: aiohttp.ClientSession, url: str, access_token: str
) -> bool | None:
    """Send a disconnect request to the server."""
    try:
        async with http.post(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=aiohttp.ClientTimeout(total=DISCONNECT_TIMEOUT),
        ) as resp:
            if resp.status < 400:
                return True
            _LOGGER.warning("Disconnect request failed with status %s", resp.status)
            return None if resp.status >= 500 else False
    except (aiohttp.ClientError, TimeoutError) as err:
        _LOGGER.warning("Disconnect request failed: %s", err)
        return None


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Notify the server when a config entry is removed."""
    url = f"{FULLFILMENT_API_URI}/disconnect-user"
    http = async_get_clientsession(hass)
    token_data = dict(entry.data.get("token") or {})

    # Refresh the token first if it is expired or about to expire.
    if token_data.get("expires_at", 0) - time.time() < TOKEN_REFRESH_MARGIN:
        _LOGGER.debug(
            "Access token is expired or expiring, refreshing before disconnect"
        )
        try:
            implementation = (
                await config_entry_oauth2_flow.async_get_config_entry_implementation(
                    hass, entry
                )
            )
            token_data = await implementation.async_refresh_token(token_data)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Token refresh failed, falling back to stored token: %s", err
            )

    access_token = token_data.get("access_token")
    if not access_token:
        _LOGGER.warning("No access token available, unable to notify server")
        return

    for attempt in range(DISCONNECT_MAX_ATTEMPTS):
        result = await _try_disconnect(http, url, access_token)
        if result is True:
            _LOGGER.debug("Server notified of disconnect")
            return
        if result is False:
            break
        if attempt < DISCONNECT_MAX_ATTEMPTS - 1:
            await asyncio.sleep(DISCONNECT_RETRY_DELAY * (attempt + 1))

    _LOGGER.warning(
        "Could not notify server of disconnect, relying on server-side cleanup"
    )
