# tune_mode.py
# ATU-100 antenna tuner integration for 50W LDMOS amp.
#
# Signal chain during tuning:
#   Radio TX -> [Attenuator IN] -> Amp -> ATU-100 -> Antenna
#
# The attenuator on the amp input reduces output power to a safe level
# (~5-10W depending on attenuator value) so the ATU-100 can tune without
# stressing the transistors during a potentially high-SWR tuning sweep.
# After tuning completes the attenuator is removed and normal operation resumes.
#
# ATU-100 interface:
#   TUNE_TRIG_GPIO  (output): pulse to start a tune cycle
#   TUNE_BUSY_GPIO  (input, optional): ATU-100 pulls LOW while tuning.
#                   If not wired, set TUNE_BUSY_GPIO = None in config;
#                   the state machine will fall back to TUNE_TIMEOUT_MS.
#
# State machine:
#   IDLE     - normal operation; tune button press starts sequence
#   ATT_IN   - attenuator relay energised; waiting for relay settle
#   TRIGGER  - pulsing ATU-100 tune trigger pin
#   WAITING  - waiting for ATU-100 busy to deassert (or timeout)
#   ATT_OUT  - attenuator relay released; waiting for settle
#
# Preconditions to start:
#   - amp_enabled must be True (amp is on and transmitting)
#   - tripped must be False
#
# Abort conditions:
#   - amp trips mid-cycle: attenuator immediately released, returns to IDLE

import utime
from machine import Pin

_IDLE    = 0
_ATT_IN  = 1
_TRIGGER = 2
_WAITING = 3
_ATT_OUT = 4

_PHASE_NAMES = {
    _IDLE:    "IDLE",
    _ATT_IN:  "ATT IN",
    _TRIGGER: "TRIGGER",
    _WAITING: "TUNING",
    _ATT_OUT: "ATT OUT",
}


class TuneMode:
    def __init__(self, cfg):
        self.cfg = cfg

        # Attenuator relay output (default off = attenuator bypassed)
        self._att_pin = Pin(cfg.TUNE_ATT_GPIO, Pin.OUT)
        self._set_att(False)

        # ATU-100 tune trigger output (default deasserted)
        self._trig_pin = Pin(cfg.TUNE_TRIG_GPIO, Pin.OUT)
        self._set_trig(False)

        # ATU-100 busy/done input (optional)
        busy_gpio = getattr(cfg, "TUNE_BUSY_GPIO", None)
        if busy_gpio is not None:
            pull = Pin.PULL_UP if getattr(cfg, "TUNE_BUSY_PULL", "UP") == "UP" else Pin.PULL_DOWN
            self._busy_pin = Pin(busy_gpio, Pin.IN, pull)
        else:
            self._busy_pin = None

        # Tune mode button
        pull = Pin.PULL_UP if getattr(cfg, "TUNE_BTN_PULL", "UP") == "UP" else Pin.PULL_DOWN
        self._btn = Pin(cfg.TUNE_BTN_GPIO, Pin.IN, pull)
        self._btn_last_level = self._btn.value()
        self._btn_last_change_ms = utime.ticks_ms()
        self._btn_consumed = False

        self._state = _IDLE
        self._state_enter_ms = 0
        self.active = False

    # --- Output helpers ---

    def _set_att(self, on):
        if getattr(self.cfg, "TUNE_ATT_ACTIVE_HIGH", True):
            self._att_pin.value(1 if on else 0)
        else:
            self._att_pin.value(0 if on else 1)

    def _set_trig(self, on):
        if getattr(self.cfg, "TUNE_TRIG_ACTIVE_HIGH", True):
            self._trig_pin.value(1 if on else 0)
        else:
            self._trig_pin.value(0 if on else 1)

    # --- Input helpers ---

    def _atu_is_busy(self):
        """Returns True while ATU-100 is still tuning."""
        if self._busy_pin is None:
            # No busy pin wired; caller falls back to timeout
            return False
        level = self._busy_pin.value()
        if getattr(self.cfg, "TUNE_BUSY_ACTIVE_LOW", True):
            return level == 0   # LOW = busy
        return level == 1       # HIGH = busy

    def _btn_event(self, now_ms):
        """Returns True exactly once per debounced button press."""
        level = self._btn.value()
        active_low = getattr(self.cfg, "TUNE_BTN_ACTIVE_LOW", True)

        if level != self._btn_last_level:
            self._btn_last_level = level
            self._btn_last_change_ms = now_ms
            self._btn_consumed = False
            return False

        if utime.ticks_diff(now_ms, self._btn_last_change_ms) < getattr(self.cfg, "TUNE_BTN_DEBOUNCE_MS", 20):
            return False

        pressed = (level == 0) if active_low else (level == 1)
        if pressed and not self._btn_consumed:
            self._btn_consumed = True
            return True
        if not pressed:
            self._btn_consumed = False
        return False

    # --- State machine ---

    def _enter(self, state, now_ms):
        self._state = state
        self._state_enter_ms = now_ms

    def _elapsed(self, now_ms):
        return utime.ticks_diff(now_ms, self._state_enter_ms)

    def update(self, amp_state, now_ms):
        """
        Call every main loop iteration.

        amp_state: dict from AmpControl.update() (previous iteration is fine;
                   5 ms lag is negligible relative to relay settle times)
        now_ms:    utime.ticks_ms()

        Returns dict:
            {
              "active": bool,  # True while a tune cycle is in progress
              "phase":  str,   # human-readable state name for display
            }
        """
        # Abort immediately if amp trips mid-cycle (relay must be safe)
        if self._state != _IDLE and amp_state.get("tripped"):
            self._abort(now_ms)

        btn = self._btn_event(now_ms)

        if self._state == _IDLE:
            # Start only if amp is on and healthy
            if btn and amp_state.get("amp_enabled") and not amp_state.get("tripped"):
                self._set_att(True)
                self._enter(_ATT_IN, now_ms)
                self.active = True

        elif self._state == _ATT_IN:
            # Wait for relay to mechanically settle, then trigger ATU-100
            if self._elapsed(now_ms) >= self.cfg.TUNE_ATT_SETTLE_MS:
                self._set_trig(True)
                self._enter(_TRIGGER, now_ms)

        elif self._state == _TRIGGER:
            # Hold trigger pulse, then release and wait for done signal
            if self._elapsed(now_ms) >= self.cfg.TUNE_TRIG_PULSE_MS:
                self._set_trig(False)
                self._enter(_WAITING, now_ms)

        elif self._state == _WAITING:
            # Wait for ATU-100 busy to deassert, or for the hard timeout.
            # If TUNE_BUSY_GPIO is None, _atu_is_busy() always returns False,
            # so we rely entirely on TUNE_TIMEOUT_MS.
            timed_out = self._elapsed(now_ms) >= self.cfg.TUNE_TIMEOUT_MS
            if timed_out or not self._atu_is_busy():
                self._set_att(False)
                self._enter(_ATT_OUT, now_ms)

        elif self._state == _ATT_OUT:
            # Brief settle so relay contacts stabilise before full power returns
            if self._elapsed(now_ms) >= self.cfg.TUNE_ATT_SETTLE_MS:
                self._enter(_IDLE, now_ms)
                self.active = False

        return {
            "active": self.active,
            "phase":  _PHASE_NAMES.get(self._state, "?"),
        }

    def _abort(self, now_ms):
        """Safe abort: deassert everything and return to IDLE immediately."""
        self._set_trig(False)
        self._set_att(False)
        self._enter(_IDLE, now_ms)
        self.active = False
