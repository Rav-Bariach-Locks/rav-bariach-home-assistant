"""Handle Sensor operations."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import RavBariachEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rav Bariach Lock sensors from a config entry."""
    hub = hass.data[DOMAIN][entry.entry_id]
    devices = hub["coordinator"].data.locks

    entities = []
    for device_data in devices:
        entities.append(RavBariachBatterySensor(hub, device_data))
        entities.append(RavBariachLockStatusSensor(hub, device_data))
        entities.append(RavBariachLockAvailabilitySensor(hub, device_data))
        entities.append(RavBariachLastUpdateSensor(hub, device_data))
    async_add_entities(entities)


class RavBariachBatterySensor(RavBariachEntity, SensorEntity):
    """Representation of a Rav Bariach Lock Battery Sensor."""

    _attr_translation_key = "battery_status"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hub, data):
        super().__init__(hub, data)
        self._attr_unique_id = f"rav_bariach_lock_battery_{self._device_id}"

    @property
    def native_value(self):
        """Return the state of the sensor (Battery Level)."""
        return self._int("batteryLevel")


class RavBariachLockStatusSensor(RavBariachEntity, SensorEntity):
    """Representation of a Rav Bariach Lock State Sensor."""

    _attr_translation_key = "lock_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["locked", "unlocked"]

    def __init__(self, hub, data):
        super().__init__(hub, data)
        self._attr_unique_id = f"rav_bariach_lock_status_{self._device_id}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return {0: "unlocked", 1: "locked"}.get(self._int("status"))

    @property
    def icon(self):
        """Return the icon of the sensor."""
        status = self._int("status")
        if status is None:
            return "mdi:lock-question"
        return "mdi:lock" if status == 1 else "mdi:lock-open-variant"


class RavBariachLockAvailabilitySensor(RavBariachEntity, SensorEntity):
    """Representation of a Rav Bariach Lock Online - Offline Sensor."""

    _attr_translation_key = "hub_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["online", "offline"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, data):
        super().__init__(hub, data)
        self._attr_unique_id = f"rav_bariach_lock_online_{self._device_id}"

    @property
    def available(self) -> bool:
        # Shows "offline" rather than going unavailable with the lock.
        return self._gateway.connected

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return "online" if self.lock_online else "offline"

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:router-wireless" if self.native_value == "online" else "mdi:router-wireless-off"


class RavBariachLastUpdateSensor(RavBariachEntity, SensorEntity):
    """When the lock last reported anything (WebSocket push or re-read)."""

    _attr_translation_key = "last_update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, data):
        super().__init__(hub, data)
        self._attr_unique_id = f"rav_bariach_lock_last_update_{self._device_id}"

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self):
        return self.last_update
