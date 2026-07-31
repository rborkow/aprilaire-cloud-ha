"""Diagnostics support for the Aprilaire Cloud integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import AprilaireCloudConfigEntry

REDACT_KEYS = {CONF_USERNAME, CONF_PASSWORD, "device_id", "deviceId"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AprilaireCloudConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = {
        device_id: asdict(device_data)
        for device_id, device_data in (coordinator.data or {}).items()
    }
    return async_redact_data(
        {
            "entry": dict(entry.data),
            "devices": data,
        },
        REDACT_KEYS,
    )
