# protection.py
# Latched protection controller:
# Trips (latches) on any fault and remains tripped until manual reset.
#
# Fault conditions:
#  1) vDrain > VDRAIN_MAX
#  2) iDrain > IDRAIN_MAX
#  3) pfwd < FWD_MIN_FRACTION * (Vcc * iDrain)
#
# Stores last_reason for later LCD display.

import utime


class Protection:
    def __init__(self, cfg):
        self.cfg = cfg
        self.tripped = False
        self.last_reason = "OK"

        self._fault_start_ms = None
        self._reset_start_ms = None

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

    def _reset_is_asserted(self, reset_level):
        """
        reset_level is the raw GPIO read: 0 or 1
        Returns True if reset condition is asserted (pressed).
        """
        if self.cfg.RESET_ACTIVE_LOW:
            return reset_level == 0
        return reset_level == 1

    def update(self, telemetry, now_ms, reset_level):
        """
        telemetry: dict (must include vDrain, iDrain, vcc, pfwd_w)
        now_ms: utime.ticks_ms()
        reset_level: current logic level of reset input (0/1)

        Returns: (shutdown: bool, reason: str)
        shutdown=True means protection output should be asserted.
        """
        # Manual reset handling (only meaningful if latched/tripped)
        if self.tripped:
            if self._reset_is_asserted(reset_level):
                if self._reset_start_ms is None:
                    self._reset_start_ms = now_ms
                elif utime.ticks_diff(now_ms, self._reset_start_ms) >= self.cfg.RESET_DEBOUNCE_MS:
                    # Clear latch
                    self.tripped = False
                    self.last_reason = "OK"
                    self._fault_start_ms = None
                    self._reset_start_ms = None
            else:
                self._reset_start_ms = None

            return True, self.last_reason  # still latched until cleared

        # Not tripped: evaluate faults with debounce
        is_fault, reason = self._fault_reason(telemetry)

        if is_fault:
            if self._fault_start_ms is None:
                self._fault_start_ms = now_ms
            elif utime.ticks_diff(now_ms, self._fault_start_ms) >= self.cfg.PROTECT_TRIP_DEBOUNCE_MS:
                self.tripped = True
                self.last_reason = reason
        else:
            self._fault_start_ms = None

        return self.tripped, (self.last_reason if self.tripped else "OK")
