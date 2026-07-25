"""Constants for the Rowenta integration."""

from datetime import timedelta
import logging

from homeassistant.const import Platform

DOMAIN = "rowenta"
LOGGER = logging.getLogger(__package__)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.VACUUM]
UPDATE_INTERVAL = timedelta(seconds=10)

# Index == cleaning_parameter_set value on the device. Confirmed against
# Home Assistant's own official ROMY integration, which shares this protocol.
FAN_SPEEDS: tuple[str, ...] = (
    "default",
    "normal",
    "silent",
    "intensive",
    "super_silent",
    "high",
    "auto",
)

# Friendly labels for the room_type values seen in get/areas. Anything not
# listed here falls back to "Room".
ROOM_TYPE_LABELS: dict[str, str] = {
    "living": "Living Room",
    "dining": "Dining Room",
    "bath": "Bathroom",
    "sleeping": "Bedroom",
    "hallway": "Hallway",
    "kitchen": "Kitchen",
    "office": "Office",
    "none": "Room",
}
