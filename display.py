# display.py
# Updated LCD renderer for 16x2 I2C LCD.

import utime
import display_config as dc
from lcd_i2c import LCD2004


def _clamp_str(s, width=16):
    s = "" if s is None else str(s)
    if len(s) < width:
        return s + (" " * (width - len(s)))
    return s[:width]


def _fmt_num(val, width, decimals=1):
    try:
        if decimals == 0:
            s = "{:d}".format(int(val))
        else:
            s = ("{0:." + str(decimals) + "f}").format(float(val))
    except:
        s = "?"
    if len(s) < width:
        s = (" " * (width - len(s))) + s
    else:
        s = s[-width:]
    return s


def _fmt_swr(swr):
    try:
        if swr == float("inf"):
            return dc.SWR_INF_TEXT.rjust(4)
        if swr > 99.9:
            return "99.9".rjust(4)
        return _fmt_num(swr, width=4, decimals=1)
    except:
        return " ?  "


class Display:
    """
    Minimal display wrapper for 16x2 LCD.
    Call update(latest, state, now_ms) periodically.
    """

    def __init__(self, i2c, addr=dc.LCD_I2C_ADDR, refresh_ms=dc.LCD_REFRESH_MS):
        self.lcd = LCD2004(i2c, addr=addr)
        self.refresh_ms = refresh_ms
        self._t_last = utime.ticks_ms()

        # Init splash, then clear
        self.lcd.clear()
        # Fit startup lines into 16 characters
        self.lcd.write_line(0, _clamp_str("HF Amp Controller", dc.LCD_COLS))
        self.lcd.write_line(1, _clamp_str("Display init OK", dc.LCD_COLS))
        utime.sleep_ms(500)
        self.lcd.clear()

    def should_refresh(self, now_ms=None):
        if now_ms is None:
            now_ms = utime.ticks_ms()
        return utime.ticks_diff(now_ms, self._t_last) >= self.refresh_ms

    def update(self, latest, state, now_ms=None):
        """
        latest: dict with telemetry (pfwd_w, prfl_w, swr, vDrain, iDrain, temp_c, ...)
        state: dict from AmpControl.update(); expects 'band_idx' key (0..2)
        """
        if now_ms is None:
            now_ms = utime.ticks_ms()

        if not self.should_refresh(now_ms):
            return

        self._t_last = now_ms

        # Telemetry defaults
        pfwd = latest.get("pfwd_w", 0.0)
        swr = latest.get("swr", float("inf"))
        vd = latest.get("vDrain", 0.0)
        id_a = latest.get("iDrain", 0.0)

        # Format values
        pfwd_s = _fmt_num(pfwd, width=4, decimals=0)   # integer W
        swr_s = _fmt_swr(swr)                          # width 4
        id_s = _fmt_num(id_a, width=4, decimals=1)     # A with 1 decimal
        vd_s = _fmt_num(vd, width=4, decimals=1)       # V with 1 decimal

        # Band label
        band_idx = int(state.get("band_idx", 0)) if state is not None else 0
        try:
            band_label = dc.BAND_LABELS[band_idx]
        except:
            band_label = dc.BAND_LABELS[0]

        # Build lines from templates and clamp
        line0 = dc.LINE0.format(swr=swr_s, pfwd=pfwd_s, band=band_label)
        line1 = dc.LINE1.format(id=id_s, vd=vd_s)

        line0 = _clamp_str(line0, dc.LCD_COLS)
        line1 = _clamp_str(line1, dc.LCD_COLS)

        # Write to the LCD
        self.lcd.write_line(0, line0)
        if dc.LCD_ROWS > 1:
            self.lcd.write_line(1, line1)
