# keyer.py
# PTT/Key input handler with debouncing
#
# Provides a Keyer class to read a PTT/key input, maintain boolean state,
# and optionally invoke a callback on state changes.

import utime
from machine import Pin


class Keyer:
    """
    Monitors a PTT/key input pin and provides a debounced boolean state.
    
    Example usage:
        keyer = Keyer(pin=15, active_low=True, debounce_ms=10, callback=my_callback)
        
        # In main loop:
        keyer.update()
        if keyer.is_active():
            # PTT is active
            pass
    """

    def __init__(self, pin, active_low=True, pull="UP", debounce_ms=10, callback=None):
        """
        Initialize the keyer.
        
        Args:
            pin: GPIO pin number for PTT/key input
            active_low: True if input is active-low (shorts to GND)
            pull: "UP" or "DOWN" for internal pull resistor
            debounce_ms: Debounce time in milliseconds
            callback: Optional function(is_active) called on state changes
        """
        self.active_low = active_low
        self.debounce_ms = debounce_ms
        self.callback = callback
        
        # Configure pin with pull resistor
        if pull == "UP":
            self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        else:
            self.pin = Pin(pin, Pin.IN, Pin.PULL_DOWN)
        
        # State tracking
        self._current_state = False  # logical state (True = active)
        self._last_level = self.pin.value()
        self._last_change_ms = utime.ticks_ms()
        self._stable = False

    def _is_active_level(self, level):
        """Convert pin level to logical active state."""
        return (level == 0) if self.active_low else (level == 1)

    def update(self, now_ms=None):
        """
        Update the keyer state. Call this frequently from main loop.
        
        Args:
            now_ms: Optional current time in milliseconds (uses ticks_ms if None)
        
        Returns:
            True if state changed, False otherwise
        """
        if now_ms is None:
            now_ms = utime.ticks_ms()
        
        level = self.pin.value()
        state_changed = False
        
        # Detect edge
        if level != self._last_level:
            self._last_level = level
            self._last_change_ms = now_ms
            self._stable = False
            return False
        
        # Check if debounce period has elapsed
        if not self._stable:
            if utime.ticks_diff(now_ms, self._last_change_ms) >= self.debounce_ms:
                self._stable = True
                
                # Update logical state
                new_state = self._is_active_level(level)
                if new_state != self._current_state:
                    self._current_state = new_state
                    state_changed = True
                    
                    # Invoke callback if provided
                    if self.callback is not None:
                        try:
                            self.callback(self._current_state)
                        except Exception as e:
                            print("Keyer callback error:", e)
        
        return state_changed

    def is_active(self):
        """
        Get the current debounced state.
        
        Returns:
            True if PTT/key is active, False otherwise
        """
        return self._current_state

    def get_raw_level(self):
        """
        Get the raw pin level (before debouncing).
        
        Returns:
            Current pin level (0 or 1)
        """
        return self.pin.value()
