"""Constants for the Rav Bariach."""

from homeassistant.const import Platform

MANUFACTURER = "Rav Bariach Smart Lock and Security Systems"
DEFAULT_NAME = "Rav Bariach Smart"
DOMAIN = "rav_bariach"

LOGIN_METHODS = ["phone", "email"]
DEFAULT_LOGIN_METHOD = "email"


AUTH_URI = "https://smarthomeslock.com/rb/sign-in-for-home-assistant"
TOKEN_URI = "https://smarthomeslock.com/api/third_part_devices/rb/home_assistant/token"
FULLFILMENT_API_URI = (
    "https://smarthomeslock.com/api/third_part_devices/rb/home_assistant/control"
)
API_URL = "https://smarthomeslock.com"
SOCKET_PATH = "/api/third_part_devices/rb/home_assistant/ws"
WS_URL = API_URL + SOCKET_PATH

PLATFORMS = [Platform.LOCK, Platform.SENSOR]
