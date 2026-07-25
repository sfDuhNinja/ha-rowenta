"""The Rowenta Robot Vacuum integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RowentaClient
from .const import PLATFORMS
from .coordinator import RowentaConfigEntry, RowentaCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: RowentaConfigEntry) -> bool:
    """Set up Rowenta from a config entry."""
    session = async_get_clientsession(hass)
    client = RowentaClient(
        session, entry.data[CONF_HOST], entry.data.get(CONF_PASSWORD, "")
    )

    if not await client.async_connect() or not client.is_unlocked:
        raise ConfigEntryNotReady(
            f"Cannot connect to Rowenta robot at {entry.data[CONF_HOST]}"
        )

    coordinator = RowentaCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: RowentaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _update_listener(hass: HomeAssistant, entry: RowentaConfigEntry) -> None:
    """Reload the entry when its options/data change."""
    await hass.config_entries.async_reload(entry.entry_id)
