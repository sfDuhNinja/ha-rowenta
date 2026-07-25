"""Local HTTP API client for Rowenta / ROMY-protocol robot vacuums.

Reverse engineered from live traffic against a Rowenta X-Plorer Series 120 AI
(firmware SER120), which speaks the same local "RobEye" HTTP protocol as
Home Assistant's official ROMY integration. No cloud, no auth for status
reads; a locked interface is unlocked with the 8-digit code printed under
the dustbin.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import FIRMWARE_MODEL_NAMES

_LOGGER = logging.getLogger(__name__)

# The device answers on whichever of these is open; ROMY-protocol robots
# have been seen on all three depending on firmware/model.
CANDIDATE_PORTS: tuple[int, ...] = (8080, 10009, 80)
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=8)


class RowentaApiError(Exception):
    """Raised when the robot's local API is unreachable or returns an error."""


class RowentaClient:
    """Thin async client for the local RobEye/ROMY-protocol HTTP API."""

    def __init__(
        self, session: aiohttp.ClientSession, host: str, password: str = ""
    ) -> None:
        """Initialize the client. Call async_connect() before anything else."""
        self._session = session
        self._host = host
        self._password = password

        self.port: int = CANDIDATE_PORTS[0]
        self.is_unlocked: bool = True
        self.unique_id: str = ""
        self.name: str = ""
        self.user_name: str = ""
        self.model: str = ""
        self.firmware: str = ""
        self.friendly_model: str = ""

    @property
    def display_name(self) -> str:
        """Best name to show for this robot.

        Prefers a nickname the user actually set in the app; falls back to
        the retail model name rather than the firmware's internal codename
        (get/robot_name reports that codename verbatim until the user
        renames the robot, so it can't be trusted as "user-set" on its own).
        """
        if self.user_name and self.user_name != self.name:
            return self.user_name
        return self.friendly_model or self.model or self.name or "Rowenta Robot Vacuum"

    async def async_connect(self) -> bool:
        """Find the reachable port, unlock if needed, and load robot identity.

        Returns False if no port answered. Raises RowentaApiError if a port
        answered but the interface could not be unlocked or identity could
        not be read.
        """
        found_port: int | None = None
        for port in CANDIDATE_PORTS:
            try:
                _, status = await self._raw_request(port, "ishttpinterfacelocked")
            except RowentaApiError:
                continue
            found_port = port
            # 400 = unlocked (bad request shape but interface answers freely),
            # 403 = locked and waiting for set/unlock_http.
            self.is_unlocked = status != 403
            break

        if found_port is None:
            return False
        self.port = found_port

        if not self.is_unlocked and len(self._password) == 8:
            try:
                await self._request("set/unlock_http", {"pass": self._password})
                self.is_unlocked = True
            except RowentaApiError:
                pass  # stays locked; identity reads below are still attempted

        # Identity reads work even while the interface is locked (locking
        # only gates set/* commands), so always attempt them - this is what
        # lets the config flow assign a stable unique_id before a password
        # has been collected.
        try:
            robot_id = await self._request("get/robot_id")
            self.unique_id = robot_id.get("unique_id", "")
            self.model = robot_id.get("model", "")
            self.firmware = robot_id.get("firmware", "")
            self.name = robot_id.get("name") or self.model or "Rowenta Robot"
            self.friendly_model = _friendly_model_name(self.firmware)

            robot_name = await self._request("get/robot_name")
            self.user_name = robot_name.get("name", "")
        except RowentaApiError:
            pass  # hard-locked firmware variant; caller sees is_unlocked=False

        return True

    async def _raw_request(
        self, port: int, path: str, params: dict[str, Any] | None = None
    ) -> tuple[str, int]:
        url = f"http://{self._host}:{port}/{path}"
        try:
            async with self._session.get(
                url, params=params, timeout=REQUEST_TIMEOUT
            ) as resp:
                text = await resp.text()
                return text, resp.status
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise RowentaApiError(f"Cannot reach {url}: {err}") from err

    async def _request(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        text, status = await self._raw_request(self.port, path, params)
        if status >= 400:
            try:
                error = json.loads(text)
            except ValueError:
                error = {"error_message": text}
            raise RowentaApiError(f"{path} failed ({status}): {error}")
        if not text:
            return {}
        try:
            return json.loads(text)
        except ValueError as err:
            raise RowentaApiError(f"{path} returned non-JSON response: {text}") from err

    # -- reads --------------------------------------------------------

    async def async_get_status(self) -> dict[str, Any]:
        """Battery, mode (maps to VacuumActivity), voltage, charging state."""
        return await self._request("get/status")

    async def async_get_wifi_status(self) -> dict[str, Any]:
        return await self._request("get/wifi_status")

    async def async_get_sensor_values(self) -> dict[str, Any]:
        return await self._request("get/sensor_values")

    async def async_get_statistics(self) -> dict[str, Any]:
        return await self._request("get/statistics")

    async def async_get_areas(self) -> dict[str, Any]:
        """Rooms/zones for the current map, including the map_id itself."""
        return await self._request("get/areas")

    # -- commands -------------------------------------------------------

    async def async_stop(self) -> None:
        await self._request("set/stop")

    async def async_go_home(self) -> None:
        await self._request("set/go_home")

    async def async_clean_start_or_continue(self, fan_speed: int) -> None:
        await self._request(
            "set/clean_start_or_continue", {"cleaning_parameter_set": fan_speed}
        )

    async def async_clean_all(self, fan_speed: int) -> None:
        await self._request(
            "set/clean_all",
            {
                "cleaning_parameter_set": fan_speed,
                "cleaning_strategy_mode": 1,
                "pump_volume": "none",
            },
        )

    async def async_clean_map(
        self, map_id: int, area_ids: list[int], fan_speed: int
    ) -> None:
        """Clean one or more rooms on the given map."""
        await self._request(
            "set/clean_map",
            {
                "map_id": map_id,
                "area_ids": ",".join(str(area_id) for area_id in area_ids),
                "cleaning_parameter_set": fan_speed,
                "cleaning_strategy_mode": 1,
                "pump_volume": "none",
            },
        )

    async def async_set_fan_speed(self, fan_speed: int) -> None:
        await self._request(
            "set/switch_cleaning_parameter_set", {"cleaning_parameter_set": fan_speed}
        )

    async def async_send_command(
        self, command: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Raw passthrough for undocumented/experimental endpoints.

        `command` is the path as used by the device, e.g. "set/clean_spot" or
        "get/maps" - with or without a leading slash.
        """
        return await self._request(command.lstrip("/"), params)


def _friendly_model_name(firmware: str) -> str:
    """Map a firmware string's series prefix to a retail model name.

    Firmware looks like "SER120-1.1.0-release:3.11.2872"; the part before
    the first "-" is the series code.
    """
    series = firmware.split("-", 1)[0] if firmware else ""
    return FIRMWARE_MODEL_NAMES.get(series, "")
