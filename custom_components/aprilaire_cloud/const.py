"""Constants for the Aprilaire Cloud integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "aprilaire_cloud"

UPDATE_INTERVAL = timedelta(seconds=60)

# The device takes ~5s to apply a PATCHed setting; refresh shortly after to
# confirm, and keep reporting the commanded value until then so polls that
# race the apply window don't flap entity state.
CONFIRM_REFRESH_DELAY = 8
COMMAND_PENDING_WINDOW = 20.0

MODE_ON = "on"
MODE_OFF = "off"
