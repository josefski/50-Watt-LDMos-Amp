# display.py
# 16x2 LCD renderer for telemetry + state
#
# Depends on lcd_i2c.py (your bring-up driver) and display_config.py

import utime
import display_config as dc
from lcd_i2c import LCD2004


def _clamp_str(s, width=16):
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
            return "INF"
        # clamp display range a bit
        if swr > 9.9:
            return "9.9"
        return _fmt_num(swr, width=3, decimals=1).strip()
    except:
        return "?"


class Display:
    """
    16x2 LCD display wrapper.
    Shows: SWR (S), Forward Power (P), Current (I), Drain Voltage (D), and band label.
    Call update(latest, state, now_ms) periodically (e.g., every LCD_REFRESH_MS).
    """

    def __init__(self, i2c, addr=dc.LCD_I2C_ADDR, refresh_ms=dc.LCD_REFRESH_MS):
        self.lcd = LCD2004(i2c, addr=addr)
        self.refresh_ms = refresh_ms
        self._t_last = utime.ticks_ms()
        self._last_lines = [""] * dc.LCD_ROWS

        self.lcd.clear()
        self.lcd.write_line(0, "HF Amp 16x2")
        self.lcd.write_line(1, "Init OK")
        utime.sleep_ms(500)

    def should_refresh(self, now_ms=None):
        if now_ms is None:
            now_ms = utime.ticks_ms()
        return utime.ticks_diff(now_ms, self._t_last) >= self.refresh_ms

    def update(self, latest, state, now_ms=None):
        """
        latest: dict with telemetry
        state: dict from AmpControl.update() including band_idx
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

        # State values
        band_idx = state.get("band_idx", 0)
        
        # Get band label
        if 0 <= band_idx < len(dc.BAND_LABELS):
            band = dc.BAND_LABELS[band_idx]
        else:
            band = "??"

        # Build line 0: SWR, Forward Power, Band
        # Format: "S:1.2 P:50 40"
        swr_s = _fmt_swr(swr)
        pfwd_s = _fmt_num(pfwd, width=3, decimals=0).strip()
        line0 = dc.LINE0.format(swr=swr_s, pfwd=pfwd_s, band=band)

        # Build line 1: Drain Voltage, Current
        # Format: "D:28.5V I:3.2A"
        vd_s = _fmt_num(vd, width=4, decimals=1).strip()
        id_s = _fmt_num(id_a, width=3, decimals=1).strip()
        line1 = dc.LINE1.format(vd=vd_s, id=id_s)

        lines = [
            _clamp_str(line0, dc.LCD_COLS),
            _clamp_str(line1, dc.LCD_COLS),
        ]

        # Only write lines that changed (reduces flicker and I2C traffic)
        for r in range(dc.LCD_ROWS):
            if lines[r] != self._last_lines[r]:
                self.lcd.write_line(r, lines[r])
                self._last_lines[r] = lines[r]
