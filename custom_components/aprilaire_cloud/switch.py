"""Switch platform for the Aprilaire Cloud integration.

The power switch mirrors the dehumidifier's mode as a plain boolean so
that external controllers (generic_hygrostat, automations) have a simple
actuator with turn_on/turn_off semantics.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MODE_OFF, MODE_ON
from .coordinator import AprilaireCloudConfigEntry, AprilaireCloudCoordinator
from .entity import AprilaireCloudEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AprilaireCloudConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        AprilaireCloudPowerSwitch(coordinator, device_id)
        for device_id in coordinator.devices
    )


class AprilaireCloudPowerSwitch(AprilaireCloudEntity, SwitchEntity):
    """On/off control mirroring the dehumidifier mode."""

    _attr_name = "Power"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: AprilaireCloudCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "power")

    @property
    def is_on(self) -> bool:
        dehumidifier = self.device_data.settings.dehumidifier
        return dehumidifier is not None and dehumidifier.mode == MODE_ON

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_mode(self._device_id, MODE_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_mode(self._device_id, MODE_OFF)
