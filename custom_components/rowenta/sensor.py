"""Diagnostic sensors for the Rowenta robot vacuum.

Battery level lives here rather than as a vacuum entity attribute: Home
Assistant deprecated VacuumEntityFeature.BATTERY / battery_level on the
vacuum entity itself (removed 2026.8) in favor of a dedicated sensor.
"""

from __future__ import annotations

from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfArea,
    UnitOfLength,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import RowentaConfigEntry, RowentaCoordinator
from .entity import RowentaEntity

SENSORS: list[SensorEntityDescription] = [
    SensorEntityDescription(
        key="battery_level",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="rssi",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="dustbin_sensor",
        translation_key="dustbin_sensor",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="total_cleaning_time",
        translation_key="total_cleaning_time",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="total_number_of_cleaning_runs",
        translation_key="total_number_of_cleaning_runs",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="runs",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="total_area_cleaned",
        translation_key="total_area_cleaned",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfArea.SQUARE_METERS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="total_distance_driven",
        translation_key="total_distance_driven",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfLength.METERS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RowentaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Rowenta sensors, skipping any the robot doesn't report."""
    coordinator = config_entry.runtime_data
    async_add_entities(
        RowentaSensor(coordinator, description)
        for description in SENSORS
        if description.key in coordinator.data.sensors
    )


class RowentaSensor(RowentaEntity, SensorEntity):
    """A single diagnostic value read from the robot."""

    entity_description: SensorEntityDescription

    def __init__(
        self, coordinator: RowentaCoordinator, entity_description: SensorEntityDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entity_description.key}_{self.client.unique_id}"
        self.entity_description = entity_description

    @property
    @override
    def native_value(self) -> float | int | None:
        """Return the current value from the coordinator's last poll."""
        return self.coordinator.data.sensors.get(self.entity_description.key)
