"""Constants for the Rowenta integration."""

from datetime import timedelta
import logging

from homeassistant.const import Platform

DOMAIN = "rowenta"
LOGGER = logging.getLogger(__package__)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.VACUUM]
UPDATE_INTERVAL = timedelta(seconds=5)

# Index == cleaning_parameter_set value on the device. The device's own
# factory debug UI labels these 0-4 as Default/Normal/Silent/Intensive/
# Super Silent, but those are internal engineering names, NOT what the
# retail Rowenta app shows - confirmed live, value by value, by switching
# the app through each of its 4 modes and reading cleaning_parameter_set
# back off the robot after each: Normal=1 (matches), Eco=2 (engineering
# "Silent"), Boost=3 (engineering "Intensive"), Silent=4 (engineering
# "Super Silent" - shortened to just "Silent" for the consumer app).
# Keep all 5 here so list index always equals the device's
# cleaning_parameter_set value; SELECTABLE_FAN_SPEEDS below is the
# narrower list to actually offer as choices.
FAN_SPEEDS: tuple[str, ...] = (
    "default",
    "normal",
    "eco",
    "boost",
    "silent",
)

# The Rowenta app itself only offers 4 speeds - "default" (index 0) is a
# fallback/internal value, not something a user picks. Confirmed against
# the live app. A room can still report/use "default" (e.g. before it's
# been customized); it just isn't offered as a new target. Ordered to match
# the app's own display order (Silent, Eco, Normal, Boost), NOT the
# device's numeric value order (Normal=1, Eco=2, Boost=3, Silent=4) - this
# is a separate, independently-ordered tuple, not a slice of FAN_SPEEDS.
SELECTABLE_FAN_SPEEDS: tuple[str, ...] = ("silent", "eco", "normal", "boost")

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
