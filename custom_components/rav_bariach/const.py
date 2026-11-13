"""Constants for the Rav Bariach."""

from homeassistant.const import Platform
from enum import IntEnum

MANUFACTURER = "Rav Bariach Smart Lock and Security Systems"
DEFAULT_NAME = "Rav Bariach Smart"
DOMAIN = "rav_bariach"

LOGIN_METHODS = ["phone", "email"]
DEFAULT_LOGIN_METHOD = "email"

PUBLIC_ID = "home_assistant"


AUTH_URI = "https://smarthomeslock.com/rb/sign-in-for-home-assistant"
TOKEN_URI = "https://smarthomeslock.com/api/third_part_devices/rb/home_assistant/token"
FULLFILMENT_API_URI = (
    "https://smarthomeslock.com/api/third_part_devices/rb/home_assistant/control"
)
API_URL = "https://smarthomeslock.com"
SOCKET_PATH = "/api/third_part_devices/rb/home_assistant/ws"
WS_URL = API_URL + SOCKET_PATH


PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.LOCK,
    Platform.SENSOR,
]


class DoorState(IntEnum):
    UNKNOWN = 0
    CLOSED = 1
    OPENED = 2

class OnlineStatus(IntEnum):
    OFFLINE = 0
    ONLINE = 1


class LockStatus(IntEnum):
    UNLOCKED = 0
    LOCKED= 1

class LockIsJammed(IntEnum):
    OK = 0
    JAMMED = 1

DISCONNECT_TIMEOUT = 10
DISCONNECT_MAX_ATTEMPTS = 3
DISCONNECT_RETRY_DELAY = 2
TOKEN_REFRESH_MARGIN = 60

# Keys under which the API may report the door contact; only the first one
# present in the lock record is used, and no door sensor is created without one.
DOOR_STATE_KEYS = ("doorState", "doorStatus", "door_state", "isDoorOpen", "doorOpen")
