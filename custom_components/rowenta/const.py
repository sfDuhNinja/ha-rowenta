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

# get/robot_id's "name" and get/robot_name both report the firmware's
# internal project codename (e.g. "Madeleine120") when the user has never
# renamed the robot in the app - not a name a buyer would recognize. Map the
# series prefix from the firmware string (e.g. "SER120-1.1.0-release" ->
# "SER120") to the retail model name instead. Extend as more models are
# confirmed; unknown series fall back to the robot's raw model code.
FIRMWARE_MODEL_NAMES: dict[str, str] = {
    "SER120": "X-Plorer Serie 120 AI",
}

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
