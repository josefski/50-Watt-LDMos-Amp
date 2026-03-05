# main.py (display/band state changes only shown; rest of main preserved)

from machine import I2C, Pin
import utime
import display

import a2d
import config
import v_drain
import current_sense
import swr_calc
import Vcc
import control
import thermistor
import band_switch

# --- Hardware bring-up ---
i2c = I2C(
    config.I2C_ID,
    scl=Pin(config.I2C_SCL_PIN),
    sda=Pin(config.I2C_SDA_PIN),
    freq=config.I2C_FREQ_HZ
)

ads = a2d.ADS1115(i2c, address=config.ADS1115_ADDR)
if not ads.probe():
    raise RuntimeError("ADS1115 not found on I2C")

vdrain = v_drain.VDrain(adc_channel=config.VDRAIN_ADC_CH, scale=config.VDRAIN_SCALE)

isense = current_sense.CurrentSense(
    adc_channel=config.CURRENT_ADC_CH,
    offset_v=config.CURRENT_OFFSET_V,
    v_per_a=config.CURRENT_V_PER_A
)

swr = swr_calc.SWRCalc(
    ads1115=ads,
    fwd_channel=config.ADS_FWD_CH,
    rfl_channel=config.ADS_RFL_CH,
    pga=config.ADS_PGA,
    data_rate=config.ADS_DATA_RATE,
    table_path=config.SWR_TABLE_PATH
)

temp = thermistor.ThermistorADS(
    ads1115=ads,
    channel=config.THERM_ADS_CH,
    csv_path=config.THERM_TABLE,
    vref=config.THERM_VREF,
    r_fixed=config.THERM_R_FIXED,
    pga=config.THERM_ADS_PGA,
    data_rate=config.THERM_ADS_DATA_RATE
)

vcc = Vcc.Vcc(adc_channel=config.VCC_ADC_CH, scale=config.VCC_SCALE)

# LCD I2C on GP2 (SDA) / GP3 (SCL)
i2c_lcd = I2C(1, sda=Pin(2), scl=Pin(3), freq=100000)
disp = display.Display(i2c_lcd)

# --- Control / Protection I/O ---
protect_out = Pin(config.PROTECT_GPIO, Pin.OUT)

bands = band_switch.BandSwitch(config)

if config.RESET_PULL == "UP":
    reset_in = Pin(config.RESET_GPIO, Pin.IN, Pin.PULL_UP)
else:
    reset_in = Pin(config.RESET_GPIO, Pin.IN, Pin.PULL_DOWN)

ctrl = control.AmpControl(config)

# Default OFF at boot => assert disable output immediately
if config.PROTECT_ACTIVE_HIGH:
    protect_out.value(1)
else:
    protect_out.value(0)

# --- Task scheduling ---
t_print = utime.ticks_ms()
t_fast = utime.ticks_ms()
t_swr = utime.ticks_ms()
t_therm = utime.ticks_ms()
t_lcd = utime.ticks_ms()

# Initialize latest/state
latest = {
    "pfwd_w": 0.0,
    "prfl_w": 0.0,
    "swr": float("inf"),
    "samples": 0,
    "vDrain": 0.0,
    "iDrain": 0.0,
    "vcc": 0.0,
    "temp_c": 0.0,
}
state = {"disable": True, "amp_enabled": False, "tripped": False, "reason": "OK", "band_idx": 0}
band_idx = config.BAND_DEFAULT_INDEX if hasattr(config, "BAND_DEFAULT_INDEX") else 0
btn_level = 1

while True:
    now = utime.ticks_ms()

    # ---------------- FAST LOOP (every pass) ----------------
    band_idx = bands.update(now_ms=now)

    btn_level = reset_in.value()
    state = ctrl.update(latest, now_ms=now, reset_btn_level=btn_level)

    # publish band index for display
    state["band_idx"] = band_idx

    # Drive protection output immediately
    if config.PROTECT_ACTIVE_HIGH:
        protect_out.value(1 if state["disable"] else 0)
    else:
        protect_out.value(0 if state["disable"] else 1)

    # (the rest of the main loop remains the same: telem reads, swr compute, lcd update, prints, sleep)
    # FAST TELEMETRY
    if utime.ticks_diff(now, t_fast) >= config.FAST_TELEM_MS:
        t_fast = now
        latest["vDrain"] = vdrain.read_drain_voltage()
        latest["iDrain"] = isense.read_current()
        latest["vcc"] = vcc.read_vcc_voltage()

    # RF TELEMETRY (SWR)
    if utime.ticks_diff(now, t_swr) >= config.SWR_AVG_WINDOW_MS:
        t_swr = now
        rf = swr.compute(window_ms=config.SWR_AVG_WINDOW_MS)
        latest["pfwd_w"] = rf.get("pfwd_w", latest["pfwd_w"])
        latest["prfl_w"] = rf.get("prfl_w", latest["prfl_w"])
        latest["swr"] = rf.get("swr", latest["swr"])
        latest["samples"] = rf.get("samples", latest["samples"])

    # THERMAL TELEMETRY
    if utime.ticks_diff(now, t_therm) >= config.THERM_TELEM_MS:
        t_therm = now
        latest["temp_c"] = temp.read_temperature()

    # LCD update
    if utime.ticks_diff(now, t_lcd) >= dc.LCD_REFRESH_MS:
        t_lcd = now
        disp.update(latest, state, now_ms=now)

    # PRINT
    if utime.ticks_diff(now, t_print) >= config.PRINT_PERIOD_MS:
        t_print = now
        print(
            "btn=", btn_level,
            "disable=", state["disable"],
            "AMP=", "ON" if state["amp_enabled"] else "OFF",
            "PROT=", ("TRIP:" + state["reason"]) if state["tripped"] else "OK",
            "Pfwd=", latest.get("pfwd_w", 0.0), "W",
            "SWR=", latest.get("swr", float("inf")),
            "Vcc=", latest.get("vcc", 0.0),
            "iDrain=", latest.get("iDrain", 0.0),
            "vDrain=", latest.get("vDrain", 0.0),
            "T=", latest.get("temp_c", 0.0), "C",
            "BAND=", band_idx + 1,
            "(n=", latest.get("samples", 0), ")"
        )

    utime.sleep_ms(5)
