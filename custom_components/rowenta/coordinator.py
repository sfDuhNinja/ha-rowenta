"""Rowenta data update coordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RowentaApiError, RowentaClient
from .const import DOMAIN, LOGGER, ROOM_TYPE_LABELS, UPDATE_INTERVAL

type RowentaConfigEntry = ConfigEntry[RowentaCoordinator]

# Binary GPIO sensors the device may report under get/sensor_values.
_SUPPORTED_BINARY_SENSORS = ("dustbin", "dock", "water_tank", "water_tank_empty")


@dataclass
class RowentaData:
    """Snapshot of everything the coordinator polls in one cycle."""

    status: dict[str, Any] = field(default_factory=dict)
    sensors: dict[str, Any] = field(default_factory=dict)
    binary_sensors: dict[str, bool] = field(default_factory=dict)
    rooms: list[dict[str, Any]] = field(default_factory=list)
    map_id: int | None = None


class RowentaCoordinator(DataUpdateCoordinator[RowentaData]):
    """Polls the robot's local HTTP API on a fixed interval."""

    config_entry: RowentaConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: RowentaConfigEntry, client: RowentaClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> RowentaData:
        """Fetch fresh state from the robot."""
        try:
            status = await self.client.async_get_status()
            wifi = await self.client.async_get_wifi_status()
            statistics = await self.client.async_get_statistics()
            sensor_values = await self.client.async_get_sensor_values()
            areas = await self.client.async_get_areas()
        except RowentaApiError as err:
            raise UpdateFailed(f"Error communicating with Rowenta robot: {err}") from err

        binary_sensors, adc_sensors = _parse_sensor_values(sensor_values)

        sensors: dict[str, Any] = {
            "battery_level": status.get("battery_level"),
            "rssi": wifi.get("rssi"),
            **adc_sensors,
            **_parse_statistics(statistics),
        }

        return RowentaData(
            status=status,
            sensors=sensors,
            binary_sensors=binary_sensors,
            rooms=_build_rooms(areas.get("areas", [])),
            map_id=areas.get("map_id"),
        )


def _parse_sensor_values(
    sensor_values: dict[str, Any],
) -> tuple[dict[str, bool], dict[str, Any]]:
    """Split get/sensor_values into binary GPIO sensors and ADC readings."""
    binary_sensors: dict[str, bool] = {}
    adc_sensors: dict[str, Any] = {}

    for sensor in sensor_values.get("sensor_data", []):
        device_type = sensor.get("device_type")

        if device_type == "gpio":
            for gpio_sensor in sensor.get("sensor_data", []):
                descriptor = gpio_sensor.get("device_descriptor")
                if descriptor in _SUPPORTED_BINARY_SENSORS:
                    value = gpio_sensor.get("payload", {}).get("data", {}).get("value")
                    binary_sensors[descriptor] = value == "active"

        elif device_type == "adc":
            for adc_sensor in sensor.get("sensor_data", []):
                if adc_sensor.get("device_descriptor") == "dustbin_sensor":
                    values = adc_sensor.get("payload", {}).get("data", {}).get("values", [])
                    if values:
                        adc_sensors["dustbin_sensor"] = values[0]

    return binary_sensors, adc_sensors


def _parse_statistics(statistics: dict[str, Any]) -> dict[str, Any]:
    """Convert the device's fixed-point counters into human units.

    Divisors match the device's own fixed-point format (confirmed against
    Home Assistant's official ROMY integration, which uses the same values).
    """
    return {
        "total_distance_driven": round(statistics.get("total_distance_driven", 0) / 128, 2),
        "total_cleaning_time": round(statistics.get("total_cleaning_time", 0) / 64, 2),
        "total_area_cleaned": round(statistics.get("total_area_cleaned", 0) / 64, 2),
        "total_number_of_cleaning_runs": statistics.get("total_number_of_cleaning_runs", 0),
    }


def _build_rooms(areas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn get/areas rooms into [{"id", "name"}], deduplicating room types.

    Only area_type == "room" entries are real, user-facing rooms; the API
    also returns "to_be_cleaned" obstacle proposals which aren't cleanable
    segments. A user-set name in area_meta_data always wins; otherwise rooms
    are labelled by room_type, with a running index when a type repeats
    (e.g. two hallways).
    """
    rooms = [area for area in areas if area.get("area_type") == "room"]

    # room_type "none" marks stale/proposed splits the robot has never
    # actually cleaned (area_state "inactive", cleaning_counter 0, never
    # last_cleaned) rather than real user-facing rooms - the app doesn't
    # show them either. Keep one only if the user has explicitly named it.
    rooms = [
        room
        for room in rooms
        if room.get("room_type", "none") != "none" or _room_custom_name(room)
    ]

    type_totals: dict[str, int] = {}
    for room in rooms:
        room_type = room.get("room_type", "none")
        type_totals[room_type] = type_totals.get(room_type, 0) + 1

    type_seen: dict[str, int] = {}
    result: list[dict[str, Any]] = []
    for room in rooms:
        custom_name = _room_custom_name(room)
        room_type = room.get("room_type", "none")

        if custom_name:
            name = custom_name
        else:
            label = ROOM_TYPE_LABELS.get(room_type, "Room")
            type_seen[room_type] = type_seen.get(room_type, 0) + 1
            name = (
                f"{label} {type_seen[room_type]}"
                if type_totals[room_type] > 1
                else label
            )

        result.append({"id": room["id"], "name": name})

    return result


def _room_custom_name(room: dict[str, Any]) -> str | None:
    """Return the user-set name from a room's area_meta_data, if any."""
    try:
        meta = json.loads(room.get("area_meta_data") or "{}")
    except ValueError:
        return None
    return meta.get("name") or None
