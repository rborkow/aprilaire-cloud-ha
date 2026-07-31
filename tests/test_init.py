"""Tests for integration setup and the coordinator's pending overlay."""

from __future__ import annotations

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.aprilaire_cloud.const import DOMAIN

from .conftest import make_settings

ENTRY_DATA = {CONF_USERNAME: "user@example.com", CONF_PASSWORD: "hunter2"}

SWITCH_ENTITY = "switch.whole_home_dehumidifier_power"
HUMIDIFIER_ENTITY = "humidifier.whole_home_dehumidifier"


async def setup_integration(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id="user@example.com"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_creates_entities(hass: HomeAssistant, mock_client) -> None:
    await setup_integration(hass)

    switch = hass.states.get(SWITCH_ENTITY)
    assert switch is not None
    assert switch.state == STATE_OFF

    humidifier = hass.states.get(HUMIDIFIER_ENTITY)
    assert humidifier is not None
    assert humidifier.state == STATE_OFF
    assert humidifier.attributes["humidity"] == 50
    assert humidifier.attributes["current_humidity"] == 47
    assert humidifier.attributes["min_humidity"] == 40
    assert humidifier.attributes["max_humidity"] == 80

    inlet = hass.states.get("sensor.whole_home_dehumidifier_inlet_air_humidity")
    assert inlet is not None
    assert float(inlet.state) == 47


async def test_switch_turn_on_is_optimistic(hass: HomeAssistant, mock_client) -> None:
    await setup_integration(hass)

    # The client still reports mode off; the switch should flip immediately.
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": SWITCH_ENTITY},
        blocking=True,
    )
    mock_client.set_dehumidifier_mode.assert_called_once()
    assert hass.states.get(SWITCH_ENTITY).state == STATE_ON
    assert hass.states.get(HUMIDIFIER_ENTITY).state == STATE_ON


async def test_pending_overlay_survives_stale_poll(
    hass: HomeAssistant, mock_client, freezer
) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    await setup_integration(hass)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": SWITCH_ENTITY}, blocking=True
    )
    assert hass.states.get(SWITCH_ENTITY).state == STATE_ON

    # A poll that still returns the stale mode must NOT flip the switch back.
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH_ENTITY).state == STATE_ON

    # Once the device confirms, the fetched value matches and sticks.
    mock_client.get_device_settings.return_value = make_settings(mode="on")
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH_ENTITY).state == STATE_ON


async def test_stale_poll_after_window_reverts(
    hass: HomeAssistant, mock_client, freezer
) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    await setup_integration(hass)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": SWITCH_ENTITY}, blocking=True
    )
    assert hass.states.get(SWITCH_ENTITY).state == STATE_ON

    # Device never applies the command; after the pending window expires the
    # fetched (real) state wins again.
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH_ENTITY).state == STATE_OFF


async def test_set_humidity(hass: HomeAssistant, mock_client) -> None:
    await setup_integration(hass)

    await hass.services.async_call(
        "humidifier",
        "set_humidity",
        {"entity_id": HUMIDIFIER_ENTITY, "humidity": 45},
        blocking=True,
    )
    mock_client.set_dehumidification_setpoint.assert_called_once()
    assert hass.states.get(HUMIDIFIER_ENTITY).attributes["humidity"] == 45


async def test_unload_entry(hass: HomeAssistant, mock_client) -> None:
    entry = await setup_integration(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH_ENTITY).state == "unavailable"
