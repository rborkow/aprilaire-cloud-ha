"""Binary sensor platform for the Aprilaire Cloud integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import (
    AprilaireCloudConfigEntry,
    AprilaireCloudCoordinator,
    DeviceData,
)
from .entity import AprilaireCloudEntity


@dataclass(frozen=True, kw_only=True)
class AprilaireCloudBinarySensorDescription(BinarySensorEntityDescription):
    """Describes an Aprilaire Cloud binary sensor."""

    value_fn: Callable[[DeviceData], bool]


DESCRIPTIONS: tuple[AprilaireCloudBinarySensorDescription, ...] = (
    AprilaireCloudBinarySensorDescription(
        key="compressor",
        name="Compressor",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.dehum_status.is_comp_on,
    ),
    AprilaireCloudBinarySensorDescription(
        key="dehum_fan",
        name="Dehumidifier fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.dehum_status.is_dehum_fan_on,
    ),
    AprilaireCloudBinarySensorDescription(
        key="hvac_fan",
        name="HVAC fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.dehum_status.is_hvac_fan_on,
    ),
    AprilaireCloudBinarySensorDescription(
        key="filter_service",
        name="Filter needs service",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.dehum_status.filter_service.needs_service,
    ),
    AprilaireCloudBinarySensorDescription(
        key="alert_high_temp",
        name="High temperature alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.dehum_status.alerts.high_temp,
    ),
    AprilaireCloudBinarySensorDescription(
        key="alert_low_temp",
        name="Low temperature alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.dehum_status.alerts.low_temp,
    ),
    AprilaireCloudBinarySensorDescription(
        key="alert_high_hum",
        name="High humidity alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.dehum_status.alerts.high_hum,
    ),
    AprilaireCloudBinarySensorDescription(
        key="alert_low_hum",
        name="Low humidity alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.dehum_status.alerts.low_hum,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AprilaireCloudConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        AprilaireCloudBinarySensor(coordinator, device_id, description)
        for device_id in coordinator.devices
        for description in DESCRIPTIONS
    )


class AprilaireCloudBinarySensor(AprilaireCloudEntity, BinarySensorEntity):
    """A boolean state from the dehumidifier status."""

    entity_description: AprilaireCloudBinarySensorDescription

    def __init__(
        self,
        coordinator: AprilaireCloudCoordinator,
        device_id: str,
        description: AprilaireCloudBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.device_data)
