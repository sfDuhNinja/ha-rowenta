"""Support for the Rowenta robot vacuum."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.vacuum import (
    Segment,
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import FAN_SPEEDS, LOGGER, SELECTABLE_FAN_SPEEDS
from .coordinator import RowentaConfigEntry, RowentaCoordinator
from .entity import RowentaEntity

SUPPORT_ROWENTA = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.STATE
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.CLEAN_AREA
    | VacuumEntityFeature.CLEAN_SPOT
    | VacuumEntityFeature.SEND_COMMAND
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RowentaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Rowenta vacuum entity."""
    async_add_entities([RowentaVacuumEntity(config_entry.runtime_data)])


class RowentaVacuumEntity(RowentaEntity, StateVacuumEntity):
    """Representation of a Rowenta robot vacuum."""

    _attr_supported_features = SUPPORT_ROWENTA
    _attr_fan_speed_list = list(SELECTABLE_FAN_SPEEDS)
    _attr_name = None

    def __init__(self, coordinator: RowentaCoordinator) -> None:
        """Initialize the vacuum entity."""
        super().__init__(coordinator)
        self._attr_unique_id = self.client.unique_id

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Update entity state from the latest coordinator data."""
        status = self.coordinator.data.status

        speed_index = status.get("cleaning_parameter_set")
        self._attr_fan_speed = (
            FAN_SPEEDS[speed_index]
            if isinstance(speed_index, int) and 0 <= speed_index < len(FAN_SPEEDS)
            else None
        )

        self._attr_activity = _activity_from_status(status)

        self.async_write_ha_state()

    def _current_fan_speed_index(self) -> int:
        """Fan speed index to use for a newly-started clean."""
        if self.fan_speed and self.fan_speed in FAN_SPEEDS:
            return FAN_SPEEDS.index(self.fan_speed)
        return self.coordinator.data.status.get("cleaning_parameter_set", 1)

    @override
    async def async_start(self) -> None:
        """Start, or resume, cleaning."""
        await self.client.async_clean_start_or_continue(self._current_fan_speed_index())

    @override
    async def async_stop(self, **kwargs: Any) -> None:
        """Stop cleaning."""
        await self.client.async_stop()

    @override
    async def async_pause(self) -> None:
        """Pause cleaning.

        The device exposes a single stop/continue pair rather than a
        distinct pause command, so pause and stop share the same call.
        """
        await self.client.async_stop()

    @override
    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Send the robot back to its dock."""
        await self.client.async_go_home()

    @override
    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set the suction/fan speed."""
        await self.client.async_set_fan_speed(FAN_SPEEDS.index(fan_speed))
        self._attr_fan_speed = fan_speed
        self.async_write_ha_state()

    @override
    async def async_clean_spot(self, **kwargs: Any) -> None:
        """Spot-clean around the robot's current position."""
        await self.client.async_clean_spot(self._current_fan_speed_index())

    @override
    async def async_get_segments(self) -> list[Segment]:
        """Return the rooms on the robot's current map."""
        return [
            Segment(id=str(room["id"]), name=room["name"])
            for room in self.coordinator.data.rooms
        ]

    @override
    async def async_clean_segments(self, segment_ids: list[str], **kwargs: Any) -> None:
        """Clean the given rooms (mapped to HA areas via the frontend)."""
        map_id = self.coordinator.data.map_id
        if map_id is None:
            LOGGER.error("Cannot clean rooms: robot reported no active map")
            return
        area_ids = [int(segment_id) for segment_id in segment_ids]
        await self.client.async_clean_map(map_id, area_ids)

    @override
    async def async_send_command(
        self,
        command: str,
        params: dict[str, Any] | list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Send a raw command to the robot's local API.

        `command` is the device's own path, e.g. "set/clean_spot" or
        "get/maps". Only mapping-style params are supported; a list is
        ignored since this device's API takes named query parameters.
        """
        query = params if isinstance(params, dict) else None
        await self.client.async_send_command(command, query)


def _activity_from_status(status: dict[str, Any]) -> VacuumActivity | None:
    """Map get/status's mode (+ charging) to a VacuumActivity.

    Confirmed live across a full stop/return/dock cycle: mode is *not* a
    direct 1:1 match to VacuumActivity's values, unlike genuine ROMY units.
    "cleaning" and "go_home" (returning to dock) match directly, but a
    stopped/idle robot and a docked-and-charging one both report the same
    mode ("ready") - charging is what tells them apart.
    """
    mode = status.get("mode")
    charging = status.get("charging")

    if mode == "cleaning":
        return VacuumActivity.CLEANING
    if mode == "go_home":
        return VacuumActivity.RETURNING
    if mode == "ready":
        # "unconnected" is the only charging value seen while undocked; treat
        # anything else (e.g. a fully-charged-but-still-docked state we
        # haven't observed a distinct string for yet) as docked too.
        return VacuumActivity.IDLE if charging == "unconnected" else VacuumActivity.DOCKED
    if mode == "error":
        return VacuumActivity.ERROR

    if mode is not None:
        LOGGER.debug("Unknown activity mode/charging combo: %s / %s", mode, charging)
    return None
