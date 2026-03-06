from machine import I2C, Pin
import utime

import a2d
import config
import v_drain
import current_sense
import swr_calc
import Vcc
import control
import thermistor
import band_switch
import keyer
import display
import display_config as dc


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

vdrain = v_drain.VDrain(
    adc_channel=config.VDRAIN_ADC_CH,
    scale=config.VDRAIN_SCALE
)

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

vcc = Vcc.Vcc(
    adc_channel=config.VCC_ADC_CH,
    scale=config.VCC_SCALE
)

# --- LCD ---
i2c_lcd = I2C(1, sda=Pin(2), scl=Pin(3), freq=100000)
disp = display.Display(i2c_lcd)

# --- Control I/O ---
protect_out = Pin(config.PROTECT_GPIO, Pin.OUT)
bands = band_switch.BandSwitch(config)

reset_in = Pin(
    config.RESET_GPIO,
    Pin.IN,
    Pin.PULL_UP if config.RESET_PULL == "UP" else Pin.PULL_DOWN
)

tx_en_out = Pin(config.TX_EN_GPIO, Pin.OUT)

# Default TX_EN OFF at boot
tx_en_out.value(0 if config.TX_EN_ACTIVE_HIGH else 1)

ptt = keyer.Keyer(
    config.KEYER_GPIO,
    active_low=config.KEYER_ACTIVE_LOW,
    pull=config.KEYER_PULL
)
ptt._debounce_ms = config.KEYER_DEBOUNCE_MS

ctrl = control.AmpControl(config)

# Default OFF at boot => assert disable output
protect_out.value(1 if config.PROTECT_ACTIVE_HIGH else 0)

# --- Scheduling ---
t_print = utime.ticks_ms()
t_fast = utime.ticks_ms()
t_swr = utime.ticks_ms()
t_therm = utime.ticks_ms()
t_lcd = utime.ticks_ms()

latest = {
    "pfwd_w": 0.0,
    "prfl_w": 0.0,
    "swr": float("inf"),
    "samples": 0,
    "vDrain": 0.0,
    "iDrain": 0.0,
    "vcc": 0.0,
    "temp_c": 0.0,
    "ptt": False,

    # keep RF volts as state (do NOT reset each loop)
    "vfwd_v": 0.0,
    "vrfl_v": 0.0,
}

state = {
    "disable": True,
    "amp_enabled": False,
    "tripped": False,
    "reason": "OK",
    "band_idx": config.BAND_DEFAULT_INDEX,
    "ptt": False,
}

band_idx = config.BAND_DEFAULT_INDEX

# IIR filter coefficient for RF detector volts (0<alpha<=1). Higher = faster response, noisier.
alpha = 0.2

# --- Hot-path aliases / cached constants ---
ticks_ms = utime.ticks_ms
ticks_diff = utime.ticks_diff
sleep_ms = utime.sleep_ms

read_ptt = ptt.update
is_keyed = ptt.is_keyed
read_reset = reset_in.value
update_band = bands.update
update_ctrl = ctrl.update
update_display = disp.update

read_vdrain = vdrain.read_drain_voltage
read_idrain = isense.read_current
read_vcc = vcc.read_vcc_voltage
read_temp = temp.read_temperature
read_ads_voltage = ads.read_voltage
interp_watts = swr.v_to_w.interp
swr_from_powers = swr_calc.swr_from_powers

fast_telem_ms = config.FAST_TELEM_MS
swr_avg_window_ms = config.SWR_AVG_WINDOW_MS
therm_telem_ms = config.THERM_TELEM_MS
lcd_refresh_ms = dc.LCD_REFRESH_MS
print_period_ms = config.PRINT_PERIOD_MS

ads_fwd_ch = config.ADS_FWD_CH
ads_rfl_ch = config.ADS_RFL_CH
ads_pga = config.ADS_PGA
ads_data_rate = config.ADS_DATA_RATE

protect_level_when_disabled = 1 if config.PROTECT_ACTIVE_HIGH else 0
protect_level_when_enabled = 0 if config.PROTECT_ACTIVE_HIGH else 1
tx_level_when_enabled = 1 if config.TX_EN_ACTIVE_HIGH else 0
tx_level_when_disabled = 0 if config.TX_EN_ACTIVE_HIGH else 1

last_protect_level = None
last_tx_level = None

while True:
    now = ticks_ms()

    # --- FAST LOOP ---
    read_ptt(now_ms=now)
    keyed = is_keyed()

    if not keyed:
        band_idx = update_band(now_ms=now)

    state = update_ctrl(latest, now_ms=now, reset_btn_level=read_reset())
    state["band_idx"] = band_idx
    state["ptt"] = keyed
    latest["ptt"] = keyed

    # Drive protection output (disable asserted when state["disable"] is True)
    protect_level = protect_level_when_disabled if state["disable"] else protect_level_when_enabled
    if protect_level != last_protect_level:
        protect_out.value(protect_level)
        last_protect_level = protect_level

    # TX enable policy: keyed AND amp allowed
    tx_en = bool(keyed and (not state["disable"]))
    tx_level = tx_level_when_enabled if tx_en else tx_level_when_disabled
    if tx_level != last_tx_level:
        tx_en_out.value(tx_level)
        last_tx_level = tx_level

    # --- FAST TELEMETRY ---
    if ticks_diff(now, t_fast) >= fast_telem_ms:
        t_fast = now
        latest["vDrain"] = read_vdrain()
        latest["iDrain"] = read_idrain()
        latest["vcc"] = read_vcc()

    # --- RF TELEMETRY (non-blocking) ---
    if ticks_diff(now, t_swr) >= swr_avg_window_ms:
        t_swr = now

        vfwd = read_ads_voltage(ads_fwd_ch, pga=ads_pga, data_rate=ads_data_rate)
        vrfl = read_ads_voltage(ads_rfl_ch, pga=ads_pga, data_rate=ads_data_rate)

        # IIR low-pass on detector volts
        latest["vfwd_v"] = latest["vfwd_v"] + alpha * (vfwd - latest["vfwd_v"])
        latest["vrfl_v"] = latest["vrfl_v"] + alpha * (vrfl - latest["vrfl_v"])

        # Volts -> Watts using calibration curve
        pfwd_w = interp_watts(latest["vfwd_v"])
        prfl_w = interp_watts(latest["vrfl_v"])
        if pfwd_w < 0.0:
            pfwd_w = 0.0
        if prfl_w < 0.0:
            prfl_w = 0.0

        latest["pfwd_w"] = pfwd_w
        latest["prfl_w"] = prfl_w
        latest["swr"] = swr_from_powers(pfwd_w, prfl_w)
        latest["samples"] = 1

    # --- THERMAL ---
    if ticks_diff(now, t_therm) >= therm_telem_ms:
        t_therm = now
        latest["temp_c"] = read_temp()

    # --- LCD ---
    if ticks_diff(now, t_lcd) >= lcd_refresh_ms:
        t_lcd = now
        update_display(latest, state, now_ms=now)

    # --- PRINT ---
    if ticks_diff(now, t_print) >= print_period_ms:
        t_print = now
        print(
            "PTT=", keyed,
            "AMP=", "ON" if state["amp_enabled"] else "OFF",
            "PROT=", ("TRIP:" + state["reason"]) if state["tripped"] else "OK",
            "Pfwd=", latest["pfwd_w"], "W",
            "SWR=", latest["swr"],
            "Vfwd=", latest["vfwd_v"], "V",
            "Vrfl=", latest["vrfl_v"], "V",
            "Vcc=", latest["vcc"],
            "I=", latest["iDrain"],
            "Vd=", latest["vDrain"],
            "T=", latest["temp_c"],
            "BAND=", band_idx + 1,
            "FWD_CH=", ads_fwd_ch,
            "RFL_CH=", ads_rfl_ch
        )

    sleep_ms(5)
