"""The Aprilaire Cloud integration."""

from __future__ import annotations

import logging

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyaprilaire_cloud.client import AprilaireCloudClient

from .coordinator import AprilaireCloudConfigEntry, AprilaireCloudCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.HUMIDIFIER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(
    hass: HomeAssistant, entry: AprilaireCloudConfigEntry
) -> bool:
    """Set up Aprilaire Cloud from a config entry."""
    client = AprilaireCloudClient(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        _LOGGER,
        session=async_get_clientsession(hass),
    )
    coordinator = AprilaireCloudCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: AprilaireCloudConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
