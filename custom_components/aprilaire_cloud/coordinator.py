"""Data update coordinator for the Aprilaire Cloud integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util
from pyaprilaire.cloud_client import (
    AprilaireCloudClient,
    CloudClientAuthError,
    CloudClientRequestError,
)
from pyaprilaire.cloud_models import (
    DehumidifierSettings,
    DehumidifierStatus,
    DeviceSettings,
    DeviceStatus,
)

from .const import (
    COMMAND_PENDING_WINDOW,
    CONFIRM_REFRESH_DELAY,
    DOMAIN,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

FIELD_MODE = "mode"
FIELD_SETPOINT = "setpoint"


@dataclass
class StaticDeviceInfo:
    """Per-device information that does not change between polls."""

    device_id: str
    room_name: str
    location_name: str
    status: DeviceStatus
    sensor_names: dict[int, str]


@dataclass
class DeviceData:
    """One device's polled state."""

    static: StaticDeviceInfo
    dehum_status: DehumidifierStatus
    settings: DeviceSettings


@dataclass
class _PendingCommand:
    value: Any
    expires_at: datetime


class AprilaireCloudCoordinator(DataUpdateCoordinator[dict[str, DeviceData]]):
    """Polls dehumidifier status and settings for all account devices."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: AprilaireCloudClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.client = client
        self.devices: dict[str, StaticDeviceInfo] = {}
        self._pending: dict[tuple[str, str], _PendingCommand] = {}

    async def _async_setup(self) -> None:
        try:
            await self.client.authenticate()
            hierarchy = await self.client.get_hierarchy()
        except CloudClientAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except CloudClientRequestError as err:
            raise UpdateFailed(f"Could not reach Aprilaire cloud: {err}") from err

        for location in hierarchy.locations:
            for room in location.rooms:
                for ref in room.devices:
                    await self._register_device(ref.device_id, room.name, location.name)

        if not self.devices:
            raise UpdateFailed("No dehumidifier devices found on this account")

    async def _register_device(
        self, device_id: str, room_name: str, location_name: str
    ) -> None:
        """Register a device if it exposes dehumidifier status."""
        try:
            status = await self.client.get_device_status(device_id)
            await self.client.get_dehumidifier_status(device_id)
            settings = await self.client.get_device_settings(device_id)
        except CloudClientAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except CloudClientRequestError:
            _LOGGER.info(
                "Skipping device %s: dehumidifier status not available", device_id
            )
            return

        sensor_names: dict[int, str] = {}
        if settings.dehumidifier:
            sensor_names = {
                sensor.uid: sensor.display_name
                for sensor in settings.dehumidifier.sensors
                if sensor.display_name
            }

        self.devices[device_id] = StaticDeviceInfo(
            device_id=device_id,
            room_name=room_name,
            location_name=location_name,
            status=status,
            sensor_names=sensor_names,
        )

    async def _async_update_data(self) -> dict[str, DeviceData]:
        data: dict[str, DeviceData] = {}
        try:
            for device_id, static in self.devices.items():
                dehum_status = await self.client.get_dehumidifier_status(device_id)
                settings = await self.client.get_device_settings(device_id)
                data[device_id] = DeviceData(
                    static=static, dehum_status=dehum_status, settings=settings
                )
        except CloudClientAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except CloudClientRequestError as err:
            raise UpdateFailed(f"Polling failed: {err}") from err

        self._apply_pending(data)
        return data

    def _apply_pending(self, data: dict[str, DeviceData]) -> None:
        """Reconcile pending commands with freshly fetched data.

        A fetched value matching the command confirms it. A mismatch inside
        the pending window means the device hasn't applied it yet, so the
        commanded value is overlaid to avoid flapping entity state (which
        would reset hysteresis timers in e.g. generic_hygrostat). A mismatch
        after the window means the device rejected the command.
        """
        now = dt_util.utcnow()
        for key, pending in list(self._pending.items()):
            device_id, field = key
            device = data.get(device_id)
            if device is None or (dehumidifier := device.settings.dehumidifier) is None:
                continue
            current = self._read_field(dehumidifier, field)
            if current == pending.value:
                del self._pending[key]
            elif now < pending.expires_at:
                data[device_id] = self._with_field(device, field, pending.value)
            else:
                _LOGGER.warning(
                    "Command %s=%s for %s was not applied by the device "
                    "(still %s); it may be out of range",
                    field,
                    pending.value,
                    device_id,
                    current,
                )
                del self._pending[key]

    @staticmethod
    def _read_field(dehumidifier: DehumidifierSettings, field: str) -> Any:
        if field == FIELD_MODE:
            return dehumidifier.mode
        return dehumidifier.humidity_setpoint

    @staticmethod
    def _with_field(device: DeviceData, field: str, value: Any) -> DeviceData:
        """Return a copy of the device data with one settings field replaced.

        Fetched objects are never mutated in place: they may be shared with
        the client or with previous coordinator data.
        """
        dehumidifier = device.settings.dehumidifier
        if dehumidifier is None:
            return device
        if field == FIELD_MODE:
            dehumidifier = replace(dehumidifier, mode=value)
        else:
            dehumidifier = replace(dehumidifier, humidity_setpoint=value)
        return replace(
            device, settings=replace(device.settings, dehumidifier=dehumidifier)
        )

    async def async_set_mode(self, device_id: str, mode: str) -> None:
        """Set the dehumidifier mode and optimistically update state."""
        await self.client.set_dehumidifier_mode(device_id, mode)
        self._record_pending(device_id, FIELD_MODE, mode)

    async def async_set_setpoint(self, device_id: str, setpoint: int) -> None:
        """Set the internal humidity setpoint and optimistically update state."""
        await self.client.set_dehumidification_setpoint(device_id, setpoint)
        self._record_pending(device_id, FIELD_SETPOINT, setpoint)

    def _record_pending(self, device_id: str, field: str, value: Any) -> None:
        self._pending[(device_id, field)] = _PendingCommand(
            value=value,
            expires_at=dt_util.utcnow() + timedelta(seconds=COMMAND_PENDING_WINDOW),
        )
        if self.data and (device := self.data.get(device_id)):
            if device.settings.dehumidifier is not None:
                new_data = dict(self.data)
                new_data[device_id] = self._with_field(device, field, value)
                self.async_set_updated_data(new_data)
        async_call_later(self.hass, CONFIRM_REFRESH_DELAY, self._confirm_refresh)

    async def _confirm_refresh(self, _now: Any) -> None:
        await self.async_request_refresh()


AprilaireCloudConfigEntry: TypeAlias = ConfigEntry[AprilaireCloudCoordinator]
