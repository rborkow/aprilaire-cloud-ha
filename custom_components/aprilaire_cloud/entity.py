"""Base entity for the Aprilaire Cloud integration."""

from __future__ import annotations

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AprilaireCloudCoordinator, DeviceData


class AprilaireCloudEntity(CoordinatorEntity[AprilaireCloudCoordinator]):
    """Base entity tied to one dehumidifier device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: AprilaireCloudCoordinator, device_id: str, key: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{key}"

        static = coordinator.devices[device_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            connections={(dr.CONNECTION_NETWORK_MAC, dr.format_mac(device_id))},
            manufacturer="Aprilaire",
            model=static.status.model or None,
            sw_version=static.status.firmware_rev or None,
            name=f"{static.room_name} Dehumidifier".strip(),
        )

    @property
    def device_data(self) -> DeviceData:
        """Return the current data for this entity's device."""
        return self.coordinator.data[self._device_id]

    @property
    def available(self) -> bool:
        return super().available and self._device_id in self.coordinator.data
