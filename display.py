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
               and optionally 'tune_active' / 'tune_phase' from TuneMode.
        """
        if now_ms is None:
            now_ms = utime.ticks_ms()

        if not self.should_refresh(now_ms):
            return

        self._t_last = now_ms

        if state is not None and state.get("tune_active"):
            self._render_tune(latest, state)
        else:
            self._render_normal(latest, state)

    def _render_normal(self, latest, state):
        pfwd = latest.get("pfwd_w", 0.0)
        swr = latest.get("swr", float("inf"))
        vd = latest.get("vDrain", 0.0)
        id_a = latest.get("iDrain", 0.0)

        pfwd_s = _fmt_num(pfwd, width=4, decimals=0)
        swr_s = _fmt_swr(swr)
        id_s = _fmt_num(id_a, width=4, decimals=1)
        vd_s = _fmt_num(vd, width=4, decimals=1)

        band_idx = int(state.get("band_idx", 0)) if state is not None else 0
        try:
            band_label = dc.BAND_LABELS[band_idx]
        except:
            band_label = dc.BAND_LABELS[0]

        line0 = _clamp_str(dc.LINE0.format(swr=swr_s, pfwd=pfwd_s, band=band_label), dc.LCD_COLS)
        line1 = _clamp_str(dc.LINE1.format(id=id_s, vd=vd_s), dc.LCD_COLS)

        self.lcd.write_line(0, line0)
        if dc.LCD_ROWS > 1:
            self.lcd.write_line(1, line1)

    def _render_tune(self, latest, state):
        """Dedicated display for ATU-100 tuning mode.

        Line 0 (16 chars): "TUNE MODE  B:40 "
        Line 1 (16 chars): "TUNING  SWR:1.2 "  (phase 8 chars + "SWR:" + 4-char swr)
        """
        swr = latest.get("swr", float("inf"))
        swr_s = _fmt_swr(swr)

        band_idx = int(state.get("band_idx", 0)) if state is not None else 0
        try:
            band_label = dc.BAND_LABELS[band_idx]
        except:
            band_label = dc.BAND_LABELS[0]

        phase = state.get("tune_phase", "TUNING")
        # phase_label is always 8 chars so "SWR:" + 4-char swr fills the line exactly
        phase_label = dc.TUNE_PHASE_LABELS.get(phase, "TUNING  ")

        line0 = _clamp_str("TUNE MODE  B:{}".format(band_label), dc.LCD_COLS)
        line1 = _clamp_str("{}SWR:{}".format(phase_label, swr_s), dc.LCD_COLS)

        self.lcd.write_line(0, line0)
        if dc.LCD_ROWS > 1:
            self.lcd.write_line(1, line1)
