"""Fixtures for Aprilaire Cloud tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pyaprilaire.cloud_models import (
    DehumidifierStatus,
    DeviceSettings,
    DeviceStatus,
    Hierarchy,
)

DEVICE_ID = "BC8D7EECB7D1"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield


def make_hierarchy() -> Hierarchy:
    return Hierarchy.from_dict(
        {
            "locations": [
                {
                    "locationId": "loc-1",
                    "name": "Home",
                    "timeZone": "America/Los_Angeles",
                    "rooms": [
                        {
                            "name": "Whole Home",
                            "devices": [
                                {
                                    "deviceId": DEVICE_ID,
                                    "access": "manage",
                                    "zone": 1,
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )


def make_device_status() -> DeviceStatus:
    return DeviceStatus.from_dict(
        {
            "deviceId": DEVICE_ID,
            "asOf": "2026-07-30T00:00:00.000Z",
            "hardwareRev": "D",
            "firmwareRev": "1.1.3",
            "altFirmwareRev": "1.9.0",
            "model": "E080W",
        }
    )


def make_dehum_status(
    *, is_comp_on: bool = False, humidity: float = 47
) -> DehumidifierStatus:
    return DehumidifierStatus.from_dict(
        {
            "deviceId": DEVICE_ID,
            "asOf": "2026-07-30T00:00:00.000Z",
            "equipmentStatus": "active" if is_comp_on else "inactive",
            "alerts": {
                "highTemp": False,
                "lowHum": False,
                "highHum": False,
                "lowTemp": False,
            },
            "fanTimeHours": 39,
            "filterService": {"needsService": False, "remaining": 100},
            "humSensors": [
                {
                    "reading": humidity,
                    "uid": 1,
                    "isControlling": True,
                    "type": "inlet-air",
                    "isWireless": False,
                    "status": "reporting",
                }
            ],
            "isCompOn": is_comp_on,
            "isDehumFanOn": is_comp_on,
            "isHvacFanOn": is_comp_on,
            "tempSensors": [
                {
                    "reading": 23.5,
                    "uid": 1,
                    "isControlling": True,
                    "type": "inlet-air",
                    "isWireless": False,
                    "status": "reporting",
                },
                {
                    "reading": 15.2,
                    "uid": 4,
                    "isControlling": False,
                    "type": "suction",
                    "isWireless": False,
                    "status": "reporting",
                },
            ],
            "wifiRSSI": -49,
        }
    )


def make_settings(*, mode: str = "off", setpoint: int = 50) -> DeviceSettings:
    return DeviceSettings.from_dict(
        {
            "deviceId": DEVICE_ID,
            "asOf": "2026-07-30T00:00:00.000Z",
            "dehumidifier": {
                "mode": mode,
                "humiditySetpoint": setpoint,
                "sensors": [
                    {"uid": 1, "dispName": "Inlet Air"},
                    {"uid": 4, "dispName": "Suction Line"},
                    {"uid": 5, "dispName": "Discharge Line"},
                ],
            },
        }
    )


@pytest.fixture
def mock_client():
    """A mocked AprilaireCloudClient wired with realistic responses."""
    client = AsyncMock()
    client.authenticate.return_value = None
    client.get_hierarchy.return_value = make_hierarchy()
    client.get_device_status.return_value = make_device_status()
    client.get_dehumidifier_status.return_value = make_dehum_status()
    client.get_device_settings.return_value = make_settings()
    client.set_dehumidifier_mode.return_value = True
    client.set_dehumidification_setpoint.return_value = True

    with (
        patch(
            "custom_components.aprilaire_cloud.AprilaireCloudClient",
            return_value=client,
        ),
        patch(
            "custom_components.aprilaire_cloud.config_flow.AprilaireCloudClient",
            return_value=client,
        ),
    ):
        yield client
