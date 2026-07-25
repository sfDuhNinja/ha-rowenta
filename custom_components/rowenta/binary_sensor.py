"""Binary status sensors for the Rowenta robot vacuum."""

from __future__ import annotations

from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import RowentaConfigEntry, RowentaCoordinator
from .entity import RowentaEntity

BINARY_SENSORS: list[BinarySensorEntityDescription] = [
    BinarySensorEntityDescription(
        key="dustbin",
        translation_key="dustbin_present",
    ),
    BinarySensorEntityDescription(
        key="dock",
        translation_key="docked",
        device_class=BinarySensorDeviceClass.PLUG,
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
        RowentaBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
        if description.key in coordinator.data.binary_sensors
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
