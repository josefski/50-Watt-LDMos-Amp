# band_switch.py
# Sequential band/filter relay control using a pushbutton.
#
# Outputs: GP4/GP5/GP6 -> buffered with NPN stage
#   Relay ON  = GPIO HIGH
#   Relay OFF = GPIO LOW
#
# Button: GP7 advances selection 0 -> 1 -> 2 -> 0
# Ensures only one relay is ON at a time.

import utime
from machine import Pin


class BandSwitch:
    def __init__(self, cfg):
        self.cfg = cfg

        # --- Outputs (push-pull) ---
        self.pins = [Pin(gp, Pin.OUT) for gp in cfg.BAND_GPIO_PINS]

        # Default selection
        self.index = int(getattr(cfg, "BAND_DEFAULT_INDEX", 0)) % len(self.pins)

        # --- Button input ---
        if cfg.BAND_BUTTON_PULL == "UP":
            self.btn = Pin(cfg.BAND_BUTTON_GPIO, Pin.IN, Pin.PULL_UP)
        else:
            self.btn = Pin(cfg.BAND_BUTTON_GPIO, Pin.IN, Pin.PULL_DOWN)

        # Debounce state
        self._last_level = self.btn.value()
        self._last_change_ms = utime.ticks_ms()
        self._press_consumed = False

        # Apply initial outputs
        self._apply_outputs()

    def _btn_is_pressed(self, level):
        return (level == 0) if self.cfg.BAND_BUTTON_ACTIVE_LOW else (level == 1)

    def _drive_pin(self, pin, on):
        """
        Drive output pin ON/OFF using simple push-pull logic.
        If BAND_ACTIVE_HIGH is True:  ON=1, OFF=0
        If BAND_ACTIVE_HIGH is False: ON=0, OFF=1 (active-low hardware)
        """
        active_high = getattr(self.cfg, "BAND_ACTIVE_HIGH", True)
        if active_high:
            pin.value(1 if on else 0)
        else:
            pin.value(0 if on else 1)

    def _apply_outputs(self):
        # Force all OFF, then selected ON (one-hot)
        for p in self.pins:
            self._drive_pin(p, on=False)
        self._drive_pin(self.pins[self.index], on=True)

    def _debounced_press_event(self, now_ms):
        """
        Returns True exactly once per valid press (debounced, one-shot).
        """
        level = self.btn.value()

        # Edge detection
        if level != self._last_level:
            self._last_level = level
            self._last_change_ms = now_ms
            return False

        # Require stable level for debounce interval
        if utime.ticks_diff(now_ms, self._last_change_ms) < self.cfg.BAND_BUTTON_DEBOUNCE_MS:
            return False

        pressed = self._btn_is_pressed(level)

        # One event per press
        if pressed and not self._press_consumed:
            self._press_consumed = True
            return True

        # On release, allow next press
        if not pressed:
            self._press_consumed = False

        return False

    def update(self, now_ms=None):
        """
        Call frequently from main loop.
        Advances band selection on each button press.
        Returns current index.
        """
        if now_ms is None:
            now_ms = utime.ticks_ms()

        if self._debounced_press_event(now_ms):
            self.index = (self.index + 1) % len(self.pins)
            self._apply_outputs()

        return self.index

    def set_index(self, idx):
        """
        Explicitly set active band (0..N-1).
        """
        self.index = int(idx) % len(self.pins)
        self._apply_outputs()
        return self.index

    def all_off(self):
        """
        Force all relays OFF.
        """
        for p in self.pins:
            self._drive_pin(p, on=False)
