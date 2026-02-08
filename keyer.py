# keyer.py
# Minimal keyer/PTT skeleton for integration with main loop.

import utime
from machine import Pin

class Keyer:
    """
    Simple keyer/PTT helper.

    Usage:
      k = Keyer(pin_no, active_low=True, pull="UP")
      k.update()        # call in fast loop
      if k.is_keyed():  # check PTT/key state
          ...
    """

    def __init__(self, gpio_pin, active_low=True, pull="UP"):
        self.gpio = Pin(gpio_pin, Pin.IN, Pin.PULL_UP if pull == "UP" else Pin.PULL_DOWN)
        self.active_low = active_low
        self._last = self.gpio.value()
        self._debounce_ms = 10
        self._last_change = utime.ticks_ms()
        self._state = False

    def _is_active_level(self, level):
        return (level == 0) if self.active_low else (level == 1)

    def update(self, now_ms=None):
        if now_ms is None:
            now_ms = utime.ticks_ms()
        lvl = self.gpio.value()
        if lvl != self._last:
            self._last = lvl
            self._last_change = now_ms
            return
        if utime.ticks_diff(now_ms, self._last_change) < self._debounce_ms:
            return
        self._state = self._is_active_level(lvl)

    def is_keyed(self):
        return bool(self._state)