"""Sensor platform for the Aprilaire Cloud integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyaprilaire.cloud_models import Sensor

from .coordinator import AprilaireCloudConfigEntry, AprilaireCloudCoordinator
from .entity import AprilaireCloudEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AprilaireCloudConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    for device_id, device in coordinator.data.items():
        for sensor in device.dehum_status.hum_sensors:
            entities.append(
                AprilaireCloudHumiditySensor(coordinator, device_id, sensor.uid)
            )
        for sensor in device.dehum_status.temp_sensors:
            entities.append(
                AprilaireCloudTemperatureSensor(coordinator, device_id, sensor.uid)
            )
        entities.append(AprilaireCloudFilterSensor(coordinator, device_id))
        entities.append(AprilaireCloudFanTimeSensor(coordinator, device_id))
        entities.append(AprilaireCloudRssiSensor(coordinator, device_id))
        entities.append(AprilaireCloudEquipmentStatusSensor(coordinator, device_id))

    async_add_entities(entities)


class _MeasurementSensor(AprilaireCloudEntity, SensorEntity):
    """A humidity or temperature reading identified by sensor uid."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _sensor_kind: str

    def __init__(
        self, coordinator: AprilaireCloudCoordinator, device_id: str, uid: int
    ) -> None:
        super().__init__(coordinator, device_id, f"{self._sensor_kind}_{uid}")
        self._uid = uid
        display_name = coordinator.devices[device_id].sensor_names.get(uid)
        kind_label = "humidity" if self._sensor_kind == "humidity" else "temperature"
        self._attr_name = (
            f"{display_name} {kind_label}" if display_name else f"{kind_label} {uid}"
        ).capitalize()

    def _find(self, sensors: list[Sensor]) -> Sensor | None:
        for sensor in sensors:
            if sensor.uid == self._uid:
                return sensor
        return None

    @property
    def _sensor(self) -> Sensor | None:
        raise NotImplementedError

    @property
    def native_value(self) -> float | None:
        sensor = self._sensor
        return sensor.reading if sensor else None

    @property
    def available(self) -> bool:
        sensor = self._sensor if super().available else None
        return sensor is not None and sensor.status == "reporting"


class AprilaireCloudHumiditySensor(_MeasurementSensor):
    """A humidity sensor reading."""

    _sensor_kind = "humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def _sensor(self) -> Sensor | None:
        return self._find(self.device_data.dehum_status.hum_sensors)


class AprilaireCloudTemperatureSensor(_MeasurementSensor):
    """A temperature sensor reading."""

    _sensor_kind = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    @property
    def _sensor(self) -> Sensor | None:
        return self._find(self.device_data.dehum_status.temp_sensors)


class AprilaireCloudFilterSensor(AprilaireCloudEntity, SensorEntity):
    """Remaining filter life."""

    _attr_name = "Filter remaining"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator: AprilaireCloudCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "filter_remaining")

    @property
    def native_value(self) -> int:
        return self.device_data.dehum_status.filter_service.remaining


class AprilaireCloudFanTimeSensor(AprilaireCloudEntity, SensorEntity):
    """Cumulative fan runtime."""

    _attr_name = "Fan runtime"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:fan-clock"

    def __init__(self, coordinator: AprilaireCloudCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "fan_time")

    @property
    def native_value(self) -> int:
        return self.device_data.dehum_status.fan_time_hours


class AprilaireCloudRssiSensor(AprilaireCloudEntity, SensorEntity):
    """Wi-Fi signal strength."""

    _attr_name = "Wi-Fi signal"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AprilaireCloudCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "rssi")

    @property
    def native_value(self) -> int:
        return self.device_data.dehum_status.wifi_rssi


class AprilaireCloudEquipmentStatusSensor(AprilaireCloudEntity, SensorEntity):
    """Raw equipment status string reported by the device."""

    _attr_name = "Equipment status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:state-machine"

    def __init__(self, coordinator: AprilaireCloudCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "equipment_status")

    @property
    def native_value(self) -> str | None:
        return self.device_data.dehum_status.equipment_status or None
