"""Handle Rav Bariach web-socket connection."""

import asyncio
import json
import logging
import re
import time
from typing import Any, Callable

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import WS_URL

_LOGGER = logging.getLogger(__name__)

# Reconnect back-off: quick retries first, then settle at 90 s.
RECONNECT_DELAYS = (5, 15, 30, 90)
# A connection that lasted this long resets the back-off.
STABLE_CONNECTION_SECONDS = 120


def parse_json_safe(data: str) -> dict[str, Any] | None:
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        try:
            fixed_data = data.replace(", ,", ",").replace(",,", ",")
            fixed_data = re.sub(r'(?<!")(\b\w+\b)(?!")(?=:)', r'"\1"', fixed_data)
            return json.loads(fixed_data)
        except (ValueError, TypeError):
            return None


class RavBariachGateway:
    """Handle the WebSocket connection and message dispatching."""

    def __init__(self, hass: HomeAssistant, session, entry):
        """Initilize the gateway connection."""
        self.hass = hass
        self._session = session
        self._listeners: dict[str, list[Callable]] = {}
        self._conn_listeners: list[Callable[[bool], None]] = []
        self._ws = None
        self._stopping = False
        self.entry = entry
        self.connected = False
        self.connect_count = 0
        self.last_message_at: float | None = None
        self.on_reconnect: Callable[[], Any] | None = None

    def register_listener(self, device_id, callback):
        """Register a callback for a specific device."""
        if device_id not in self._listeners:
            self._listeners[device_id] = []
        self._listeners[device_id].append(callback)

        def remove_listener():
            if device_id in self._listeners and callback in self._listeners[device_id]:
                self._listeners[device_id].remove(callback)

        return remove_listener

    def register_connection_listener(self, callback: Callable[[bool], None]):
        """Register a callback that gets the connection state on every change."""
        self._conn_listeners.append(callback)

        def remove_listener():
            if callback in self._conn_listeners:
                self._conn_listeners.remove(callback)

        return remove_listener

    def _set_connected(self, value: bool) -> None:
        if self.connected == value:
            return
        self.connected = value
        for callback in list(self._conn_listeners):
            try:
                callback(value)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Connection listener error")

    async def start_listen(self) -> None:
        """Start the WebSocket listening."""
        _LOGGER.debug("Gateway starts listening...")
        websession = async_get_clientsession(self.hass)
        attempt = 0

        while not self._stopping:
            connected_at = None
            try:
                try:
                    await self._session.async_ensure_token_valid()
                except Exception as err:  # pylint: disable=broad-except
                    if getattr(err, "status", None) == 429:
                        _LOGGER.warning("Token refresh rate limit hit. Retrying later.")
                    else:
                        _LOGGER.warning("Token refresh failed: %s", err)
                    raise

                token = self._session.token["access_token"]

                _LOGGER.debug("Connecting to WebSocket...")
                async with websession.ws_connect(
                    WS_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Client-Type": "HomeAssistant",
                        "Connection": "Upgrade",
                        "Upgrade": "websocket",
                    },
                    heartbeat=30,
                ) as ws:
                    self._ws = ws
                    connected_at = time.monotonic()
                    self.connect_count += 1
                    _LOGGER.info("WebSocket connected (connection #%s)", self.connect_count)
                    self._set_connected(True)

                    if self.connect_count > 1 and self.on_reconnect is not None:
                        # State may have changed while we were away.
                        self.hass.async_create_task(self.on_reconnect())

                    async for msg in ws:
                        if self._stopping:
                            break

                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_message_async(msg.data)

                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            _LOGGER.warning("WebSocket closed by the server")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            _LOGGER.error("WebSocket error: %s", ws.exception())
                            break

            except aiohttp.ClientError as client_err:
                _LOGGER.error("WebSocket connection error: %s", client_err)
            except asyncio.CancelledError:
                raise
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("WebSocket connection error")
            finally:
                self._ws = None
                self._set_connected(False)

            if self._stopping:
                break

            if connected_at and time.monotonic() - connected_at > STABLE_CONNECTION_SECONDS:
                attempt = 0
            delay = RECONNECT_DELAYS[min(attempt, len(RECONNECT_DELAYS) - 1)]
            attempt += 1
            _LOGGER.debug("Socket disconnected, retrying in %s seconds...", delay)
            await asyncio.sleep(delay)

    async def _handle_message_async(self, data: str):
        """Process incoming WebSocket messages without blocking the event loop."""
        _LOGGER.debug("WS message: %s", data)
        self.last_message_at = time.time()

        json_data = parse_json_safe(data)

        if json_data is None:
            _LOGGER.warning(
                "Incoming data could not be parsed to JSON: %s...", data[:50]
            )
            return

        try:
            device_id = str(json_data.get("deviceId"))

            if device_id == "None":
                internal_data = json_data.get("data", {})
                device_id = str(internal_data.get("deviceId"))

            payload = json_data.get("data", {})
            if not payload:
                payload = json_data

            if device_id and device_id in self._listeners:
                for callback in self._listeners[device_id]:
                    try:
                        callback(payload)
                    except Exception:  # pylint: disable=broad-except
                        _LOGGER.exception(
                            "Callback execution error for device: %s", device_id
                        )
            else:
                _LOGGER.debug("No active listener found for device: %s", device_id)

        except (KeyError, TypeError, ValueError):
            _LOGGER.exception("Message payload processing error")

    async def async_disconnect(self):
        """Disconnect the gateway and stop the background loop."""
        _LOGGER.info("Shutting down gateway...")
        self._stopping = True

        if self._ws:
            await self._ws.close()
