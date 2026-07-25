"""Base entity for Rowenta."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RowentaCoordinator


class RowentaEntity(CoordinatorEntity[RowentaCoordinator]):
    """Base Rowenta entity, shared by the vacuum, sensor and binary_sensor platforms."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RowentaCoordinator) -> None:
        """Initialize the entity and its device registry entry."""
        super().__init__(coordinator)
        self.client = coordinator.client
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.client.unique_id)},
            manufacturer="Rowenta",
            name=self.client.display_name,
            model=self.client.friendly_model or self.client.model,
            sw_version=self.client.firmware,
        )
