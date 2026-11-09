"""Binary sensors: door contact (when the API reports one), jammed, online."""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DOOR_STATE_KEYS, DoorState, LockIsJammed
from .entity import RavBariachEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][entry.entry_id]
    devices = hub["coordinator"].data.locks

    entities = []
    for device_data in devices:
        _LOGGER.debug("Lock %s record keys: %s", device_data.get("deviceId"), sorted(device_data))
        door_key = next((k for k in DOOR_STATE_KEYS if k in device_data), None)
        if door_key:
            entities.append(RavBariachDoorSensor(hub, device_data, door_key))
        if "isJammed" in device_data:
            entities.append(RavBariachJammedSensor(hub, device_data))
        entities.append(RavBariachOnlineSensor(hub, device_data))
    async_add_entities(entities)


class RavBariachDoorSensor(RavBariachEntity, BinarySensorEntity):
    _attr_translation_key = "door"
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, hub, data, key):
        super().__init__(hub, data)
        self._key = key
        self._attr_unique_id = f"rav_bariach_lock_door_{self._device_id}"

    @property
    def is_on(self) -> bool | None:
        val = self._data.get(self._key)
        if isinstance(val, bool):
            return val
        ival = self._int(self._key)
        if ival is None or ival == DoorState.UNKNOWN:
            return None
        return ival == DoorState.OPENED


class RavBariachJammedSensor(RavBariachEntity, BinarySensorEntity):
    _attr_translation_key = "jammed"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, data):
        super().__init__(hub, data)
        self._attr_unique_id = f"rav_bariach_lock_jammed_{self._device_id}"

    @property
    def is_on(self) -> bool | None:
        val = self._int("isJammed")
        return None if val is None else val == LockIsJammed.JAMMED


class RavBariachOnlineSensor(RavBariachEntity, BinarySensorEntity):
    """Lock reachable through its hub, as reported by the cloud."""

    _attr_translation_key = "online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, data):
        super().__init__(hub, data)
        self._attr_unique_id = f"rav_bariach_lock_online_bs_{self._device_id}"

    @property
    def available(self) -> bool:
        return self._gateway.connected

    @property
    def is_on(self) -> bool:
        return self.lock_online
