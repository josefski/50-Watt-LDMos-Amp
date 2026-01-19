# display.py
# Minimal LCD renderer for telemetry + state
#
# Depends on lcd_i2c.py (your bring-up driver) and display_config.py

import utime
import display_config as dc
from lcd_i2c import LCD2004


def _clamp_str(s, width=20):
    # Pad/truncate to exactly LCD width for clean overwrites
    s = "" if s is None else str(s)
    if len(s) < width:
        return s + (" " * (width - len(s)))
    return s[:width]


def _fmt_num(val, width, decimals=1):
    """
    Formats a number into a fixed-width field.
    Returns a string of exactly 'width' chars (right-justified).
    """
    try:
        if decimals == 0:
            s = "{:d}".format(int(val))
        else:
            s = ("{0:." + str(decimals) + "f}").format(float(val))
    except:
        s = "?"  # if missing/invalid

    # Right-justify to requested width
    if len(s) < width:
        s = (" " * (width - len(s))) + s
    else:
        s = s[-width:]  # take rightmost if too long
    return s


def _fmt_swr(swr):
    try:
        if swr == float("inf"):
            return dc.SWR_INF_TEXT
        # clamp display range a bit
        if swr > 99.9:
            return "99.9"
        return _fmt_num(swr, width=4, decimals=1).strip()
    except:
        return "?"


class Display:
    """
    Minimal display wrapper.
    Call update(latest, state, now_ms) periodically (e.g., every LCD_REFRESH_MS).
    """

    def __init__(self, i2c, addr=dc.LCD_I2C_ADDR, refresh_ms=dc.LCD_REFRESH_MS):
        self.lcd = LCD2004(i2c, addr=addr)
        self.refresh_ms = refresh_ms
        self._t_last = utime.ticks_ms()
        self._last_lines = [""] * dc.LCD_ROWS

        self.lcd.clear()
        self.lcd.write_line(0, "HF Amp Controller")
        self.lcd.write_line(1, "Display init OK")
        self.lcd.write_line(2, "Addr: " + hex(addr))
        self.lcd.write_line(3, "")
        utime.sleep_ms(500)

    def should_refresh(self, now_ms=None):
        if now_ms is None:
            now_ms = utime.ticks_ms()
        return utime.ticks_diff(now_ms, self._t_last) >= self.refresh_ms

    def update(self, latest, state, now_ms=None):
        """
        latest: dict with telemetry
        state: dict from AmpControl.update()
        """
        if now_ms is None:
            now_ms = utime.ticks_ms()

        if not self.should_refresh(now_ms):
            return

        self._t_last = now_ms

        # Telemetry values (with robust defaults)
        pfwd = latest.get("pfwd_w", 0.0)
        swr = latest.get("swr", float("inf"))
        vd = latest.get("vDrain", 0.0)
        id_a = latest.get("iDrain", 0.0)
        tc = latest.get("temp_c", None)

        # State values
        amp_on = bool(state.get("amp_enabled", False))
        tripped = bool(state.get("tripped", False))
        reason = state.get("reason", "OK")

        # Build line 0: PFWD and SWR
        pfwd_s = _fmt_num(pfwd, width=5, decimals=0).strip()
        swr_s = _fmt_swr(swr)
        line0 = dc.LINE0.format(pfwd=pfwd_s, swr=swr_s)

        # Build line 1: V/I
        vd_s = _fmt_num(vd, width=5, decimals=1).strip()
        id_s = _fmt_num(id_a, width=4, decimals=1).strip()
        line1 = dc.LINE1.format(vd=vd_s, id=id_s)

        # Build line 2: Temp
        if tc is None:
            tc_s = " ? "
        else:
            tc_s = _fmt_num(tc, width=5, decimals=1).strip()
        line2 = dc.LINE2.format(tc=tc_s)

        # Build line 3: status
        if tripped:
            # Keep it simple and readable; LCD is 20 chars
            # Example: "FAULT:THERM_OT     "
            line3 = (dc.STATUS_FAULT_PREFIX + str(reason))
        else:
            line3 = dc.STATUS_OK_ON if amp_on else dc.STATUS_OK_OFF

        lines = [
            _clamp_str(line0, dc.LCD_COLS),
            _clamp_str(line1, dc.LCD_COLS),
            _clamp_str(line2, dc.LCD_COLS),
            _clamp_str(line3, dc.LCD_COLS),
        ]

        # Only write lines that changed (reduces flicker and I2C traffic)
        for r in range(dc.LCD_ROWS):
            if lines[r] != self._last_lines[r]:
                self.lcd.write_line(r, lines[r])
                self._last_lines[r] = lines[r]
