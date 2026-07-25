"""Binary status sensors for the Rowenta robot vacuum."""

from __future__ import annotations

from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import RowentaConfigEntry, RowentaCoordinator
from .entity import RowentaEntity

# "dock" is intentionally not exposed here - it's the same signal as the
# vacuum entity's own DOCKED activity state, so a separate sensor would
# just duplicate it.
BINARY_SENSORS: list[BinarySensorEntityDescription] = [
    BinarySensorEntityDescription(
        key="dustbin",
        translation_key="dustbin_present",
    ),
    BinarySensorEntityDescription(
        key="water_tank",
        translation_key="water_tank_present",
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
    BinarySensorEntityDescription(
        key="water_tank_empty",
        translation_key="water_tank_empty",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RowentaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Rowenta binary sensors, skipping any the robot doesn't report."""
    coordinator = config_entry.runtime_data
    async_add_entities(
        [
            RowentaBinarySensor(coordinator, description)
            for description in BINARY_SENSORS
            if description.key in coordinator.data.binary_sensors
        ]
        + [RowentaProblemBinarySensor(coordinator)]
    )


class RowentaBinarySensor(RowentaEntity, BinarySensorEntity):
    """A single binary status value read from the robot."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: RowentaCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entity_description.key}_{self.client.unique_id}"
        self.entity_description = entity_description

    @property
    @override
    def is_on(self) -> bool:
        """Return the current value from the coordinator's last poll."""
        return bool(self.coordinator.data.binary_sensors.get(self.entity_description.key))


class RowentaProblemBinarySensor(RowentaEntity, BinarySensorEntity):
    """Reports the robot's own get/robot_flags error/not_ready state.

    "notification" entries (e.g. water_tank_inserted) are informational,
    not problems, so they don't drive is_on - all three lists are exposed
    as attributes for detail regardless.
    """

    _attr_translation_key = "problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: RowentaCoordinator) -> None:
        """Initialize the problem binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"problem_{self.client.unique_id}"

    @property
    @override
    def is_on(self) -> bool:
        """True if the robot reports a stuck component or similar error."""
        flags = self.coordinator.data.robot_flags
        return bool(flags.get("error") or flags.get("not_ready"))

    @property
    @override
    def extra_state_attributes(self) -> dict[str, list[str]]:
        """The raw error/not_ready/notification flag lists, e.g. stuck_wheel."""
        flags = self.coordinator.data.robot_flags
        return {
            "error": flags.get("error", []),
            "not_ready": flags.get("not_ready", []),
            "notification": flags.get("notification", []),
        }
