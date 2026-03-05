# control.py
# Combined amp enable toggle + latched protection (manual clear)
#
# Output behavior:
#   output_disable == True  => drive protection/disable output (amp OFF)
#   output_disable == False => allow amp ON
#
# Policy:
#   - Boot defaults to amp OFF
#   - Button press toggles amp ON/OFF when NOT tripped
#   - If tripped, button press clears fault latch BUT amp remains OFF
#   - Trips latch on any fault condition (debounced)

import utime


class AmpControl:
    def __init__(self, cfg):
        self.cfg = cfg
        
        self._therm_start_ms = None


        # Default: amp OFF at boot
        self.amp_enabled = False

        # Protection latch
        self.tripped = False
        self.last_reason = "OK"

        # Debounce state
        self._fault_start_ms = None
        self._btn_last_level = None
        self._btn_last_change_ms = None
        self._btn_press_consumed = False  # ensures one action per press

    def _btn_is_pressed(self, level):
        # level is raw GPIO read (0/1)
        return (level == 0) if self.cfg.RESET_ACTIVE_LOW else (level == 1)

    def _fault_reason(self, telemetry):
        v_drain = telemetry.get("vDrain", 0.0)
        i_drain = telemetry.get("iDrain", 0.0)
        vcc     = telemetry.get("vcc", 0.0)
        pfwd    = telemetry.get("pfwd_w", 0.0)

        if v_drain > self.cfg.PROTECT_VDRAIN_MAX_V:
            return True, "VDRAIN_OV"

        if i_drain > self.cfg.PROTECT_IDRAIN_MAX_A:
            return True, "IDRAIN_OC"
        
        total_p = vcc * i_drain
        if (i_drain >= self.cfg.PROTECT_MIN_I_FOR_EFF_A) and (total_p >= self.cfg.PROTECT_MIN_TOTAL_POWER_W):
            min_pfwd = self.cfg.PROTECT_FWD_MIN_FRACTION * total_p
            if pfwd < min_pfwd:
                return True, "FWD_LOW_VS_VI"

        return False, "OK"
    
        # Thermal over-temperature (handled with debounce in update(), not here)
        # We return a fault indication here if temp is over threshold; update()
        # will apply the time qualification.
        temp_c = telemetry.get("temp_c", None)
        if temp_c is not None and temp_c >= self.cfg.PROTECT_TEMP_MAX_C:
            return True, "THERM_OT"


    def _debounced_button_event(self, now_ms, level):
        """
        Returns True exactly once per debounced press.
        """
        if self._btn_last_level is None:
            self._btn_last_level = level
            self._btn_last_change_ms = now_ms
            return False

        if level != self._btn_last_level:
            self._btn_last_level = level
            self._btn_last_change_ms = now_ms
            self._btn_press_consumed = False
            return False

        # Stable level for >= debounce interval
        if utime.ticks_diff(now_ms, self._btn_last_change_ms) < self.cfg.RESET_DEBOUNCE_MS:
            return False

        pressed = self._btn_is_pressed(level)

        # One event per press
        if pressed and not self._btn_press_consumed:
            self._btn_press_consumed = True
            return True

        # When released, allow next press to generate event
        if not pressed:
            self._btn_press_consumed = False

        return False

    def update(self, telemetry, now_ms, reset_btn_level):
        """
        Returns a dict describing the control state:
          {
            "disable": bool,        # True => force amp OFF (assert disable output)
            "amp_enabled": bool,    # requested enable (if not tripped)
            "tripped": bool,
            "reason": str
          }
        """
        # 1) Evaluate electrical protection (fast debounce) and latch on trip
        is_fault, reason = self._fault_reason(telemetry)

        if not self.tripped:
            if is_fault:
                if self._fault_start_ms is None:
                    self._fault_start_ms = now_ms
                elif utime.ticks_diff(now_ms, self._fault_start_ms) >= self.cfg.PROTECT_TRIP_DEBOUNCE_MS:
                    self.tripped = True
                    self.last_reason = reason
                    self.amp_enabled = False
            else:
                self._fault_start_ms = None

        # 2) Thermal protection (slow debounce) - trips only if sustained overtemp
        temp_c = telemetry.get("temp_c", None)
        overtemp = (temp_c is not None) and (temp_c >= self.cfg.PROTECT_TEMP_MAX_C)

        if not self.tripped:
            if overtemp:
                if self._therm_start_ms is None:
                    self._therm_start_ms = now_ms
                elif utime.ticks_diff(now_ms, self._therm_start_ms) >= self.cfg.PROTECT_THERM_DEBOUNCE_MS:
                    self.tripped = True
                    self.last_reason = "THERM_OT"
                    self.amp_enabled = False
            else:
                self._therm_start_ms = None
        else:
            self._therm_start_ms = None

        # 3) Handle button press event
        pressed_event = self._debounced_button_event(now_ms, reset_btn_level)
        if pressed_event:
            if self.tripped:
                # Clear trip latch, but keep amp OFF (requires second press to enable)
                self.tripped = False
                self.last_reason = "OK"
                self._fault_start_ms = None
                self._therm_start_ms = None
                self.amp_enabled = False
            else:
                # Toggle enable state
                self.amp_enabled = not self.amp_enabled

        # 4) Determine output disable state
        disable = (not self.amp_enabled) or self.tripped

        return {
            "disable": disable,
            "amp_enabled": self.amp_enabled,
            "tripped": self.tripped,
            "reason": (self.last_reason if self.tripped else "OK")
        }
