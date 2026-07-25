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
        [
            RowentaSensor(coordinator, description)
            for description in SENSORS
            if description.key in coordinator.data.sensors
        ]
        + [RowentaLastRunDurationSensor(coordinator)]
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


class RowentaLastRunDurationSensor(RowentaEntity, SensorEntity):
    """How long the most recent actual cleaning run took, from get/task_history."""

    _attr_translation_key = "last_run_duration"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: RowentaCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"last_run_duration_{self.client.unique_id}"

    @property
    @override
    def native_value(self) -> float | None:
        """Duration in minutes of the most recent clean_map/clean_all/clean_spot task."""
        last_run = self.coordinator.data.last_run
        return last_run["duration_minutes"] if last_run else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, object]:
        """Area cleaned, outcome, task type and end time of that same run."""
        last_run = self.coordinator.data.last_run
        if not last_run:
            return {}
        return {
            "area_cleaned_m2": last_run["area_cleaned"],
            "state": last_run["state"],
            "task_type": last_run["task_type"],
            "ended_at": last_run["ended_at"],
        }
