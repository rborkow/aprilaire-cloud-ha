# Aprilaire Cloud for Home Assistant

Control Aprilaire E-series WiFi dehumidifiers (tested on the E080W) through
the Aprilaire cloud API — the same API the AprilAire Healthy Air app uses.
Built on [pyaprilaire](https://github.com/chamberlain2007/pyaprilaire).

This integration is independent of (and can coexist with) the core
`aprilaire` integration, which talks to 8800/6000-series thermostats over
the local socket protocol.

## Entities

Per dehumidifier:

- **Humidifier** (dehumidifier device class): mode on/off, the internal
  humidity setpoint (40–80 %), current inlet humidity, and running action
- **Switch** "Power": a plain on/off actuator mirroring the mode, intended
  for external controllers such as `generic_hygrostat`
- **Sensors**: per-sensor humidity and temperature readings (inlet air,
  suction line, discharge line), filter remaining, fan runtime,
  Wi-Fi signal (disabled by default), equipment status
- **Binary sensors**: compressor, fans, filter service, alert flags

## Installation

1. HACS → Custom repositories → add this repository URL, category
   **Integration**, then download **Aprilaire Cloud**.
2. Restart Home Assistant.
3. Settings → Devices & services → Add integration → **Aprilaire Cloud**,
   and sign in with your AprilAire Healthy Air account.

## External control with generic_hygrostat

The dehumidifier's own control loop uses its inlet-air sensor, which often
reads drier than the living space. To drive the unit from a room sensor
(a thermostat's humidity reading, for example):

1. **One-time prep**: set the humidifier entity's target humidity to the
   minimum (40 %). With the inlet sensor effectively bypassed, mode "on"
   then means "run". The internal setpoint remains a hardware backstop: if
   your automation stops, the unit still self-limits at 40 % inlet RH.
2. Add a [generic_hygrostat](https://www.home-assistant.io/integrations/generic_hygrostat/)
   to `configuration.yaml`:

```yaml
generic_hygrostat:
  - name: Whole Home Dehumidifier
    device_class: dehumidifier
    humidifier: switch.whole_home_dehumidifier_power
    target_sensor: sensor.your_room_humidity
    target_humidity: 52
    wet_tolerance: 3      # turns on at >= 55%
    dry_tolerance: 2      # turns off at <= 50%
    min_cycle_duration:
      minutes: 10         # compressor short-cycle protection
    sensor_stale_duration:
      hours: 2            # frozen sensor -> turn off for safety
    initial_state: true
```

The hygrostat's own humidifier entity then carries the *room* target, while
this integration's humidifier entity shows the device's internal setpoint.

## Notes

- Polling interval is 60 seconds. Commands apply on the device in ~5
  seconds; entity state updates optimistically and is confirmed on the
  next refresh.
- Setpoint writes outside 40–80 % are silently ignored by the device
  (the API accepts them but the unit never applies them); the entity
  min/max prevents this.
- The cloud API is unofficial and may change without notice.
