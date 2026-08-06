"""Humidifier platform for the Aprilaire Cloud integration.

Exposes the dehumidifier's native controls: mode on/off and the internal
humidity setpoint, which is evaluated against the unit's own inlet-air
sensor. For external control (e.g. generic_hygrostat driven by a room
sensor), use the power switch entity and pin this setpoint at the minimum.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.humidifier import (
    HumidifierAction,
    HumidifierDeviceClass,
    HumidifierEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyaprilaire_cloud.const import (
    DEHUMIDIFICATION_SETPOINT_MAX,
    DEHUMIDIFICATION_SETPOINT_MIN,
)

from .const import MODE_OFF, MODE_ON
from .coordinator import AprilaireCloudConfigEntry, AprilaireCloudCoordinator
from .entity import AprilaireCloudEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AprilaireCloudConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the humidifier platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        AprilaireCloudDehumidifier(coordinator, device_id)
        for device_id in coordinator.devices
    )


class AprilaireCloudDehumidifier(AprilaireCloudEntity, HumidifierEntity):
    """The dehumidifier's native representation."""

    _attr_name = None
    _attr_device_class = HumidifierDeviceClass.DEHUMIDIFIER
    _attr_min_humidity = DEHUMIDIFICATION_SETPOINT_MIN
    _attr_max_humidity = DEHUMIDIFICATION_SETPOINT_MAX

    def __init__(self, coordinator: AprilaireCloudCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "dehumidifier")

    @property
    def _mode(self) -> str | None:
        dehumidifier = self.device_data.settings.dehumidifier
        return dehumidifier.mode if dehumidifier else None

    @property
    def is_on(self) -> bool:
        mode = self._mode
        if mode not in (MODE_ON, MODE_OFF, None):
            _LOGGER.debug("Unknown dehumidifier mode %s treated as off", mode)
        return mode == MODE_ON

    @property
    def target_humidity(self) -> int | None:
        dehumidifier = self.device_data.settings.dehumidifier
        return dehumidifier.humidity_setpoint if dehumidifier else None

    @property
    def current_humidity(self) -> float | None:
        for sensor in self.device_data.dehum_status.hum_sensors:
            if sensor.is_controlling:
                return sensor.reading
        return None

    @property
    def action(self) -> HumidifierAction:
        if not self.is_on:
            return HumidifierAction.OFF
        if self.device_data.dehum_status.is_comp_on:
            return HumidifierAction.DRYING
        return HumidifierAction.IDLE

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_mode(self._device_id, MODE_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_mode(self._device_id, MODE_OFF)

    async def async_set_humidity(self, humidity: int) -> None:
        await self.coordinator.async_set_setpoint(self._device_id, int(humidity))
