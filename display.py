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


class Display:
    """
    Minimal display wrapper for 16x2 LCD.
    Call update(latest, state, now_ms) periodically.
    """

    def __init__(self, i2c, addr=dc.LCD_I2C_ADDR, refresh_ms=dc.LCD_REFRESH_MS):
        self.lcd = LCD2004(i2c, addr=addr)
        self.refresh_ms = refresh_ms
        self._t_last = utime.ticks_ms()

        self.lcd.clear()
        self.lcd.write_line(0, _clamp_str("HF Amp Controller", dc.LCD_COLS))
        self.lcd.write_line(1, _clamp_str("Display init OK", dc.LCD_COLS))
        utime.sleep_ms(500)
        self.lcd.clear()

    def should_refresh(self, now_ms=None):
        if now_ms is None:
            now_ms = utime.ticks_ms()
        return utime.ticks_diff(now_ms, self._t_last) >= self.refresh_ms

    def update(self, latest, state, now_ms=None):
        if now_ms is None:
            now_ms = utime.ticks_ms()

        if not self.should_refresh(now_ms):
            return

        self._t_last = now_ms

        pfwd = latest.get("pfwd_w", 0.0)
        swr  = latest.get("swr", float("inf"))
        vd   = latest.get("vDrain", 0.0)
        id_a = latest.get("iDrain", 0.0)

        pfwd_s = _fmt_num(pfwd, width=2, decimals=0)
        id_s   = _fmt_num(id_a, width=2, decimals=1)
        vd_s   = _fmt_num(vd,   width=2, decimals=1)

        if swr == float("inf") or swr > 99:
            swr_s = "--"
        else:
            swr_s = _fmt_num(swr, width=2, decimals=0)

        band_idx = int(state.get("band_idx", 0)) if state is not None else 0
        try:
            band_label = dc.BAND_LABELS[band_idx]
        except:
            band_label = dc.BAND_LABELS[0]

        line0 = dc.LINE0.format(swr=swr_s, pfwd=pfwd_s, band=band_label)
        line1 = dc.LINE1.format(ia=id_s, vd=vd_s)

        self.lcd.write_line(0, _clamp_str(line0, dc.LCD_COLS))
        if dc.LCD_ROWS > 1:
            self.lcd.write_line(1, _clamp_str(line1, dc.LCD_COLS))
