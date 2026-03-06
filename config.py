# Central configuration for Pico HF Amp controller

import a2d

# --- I2C / ADS1115 wiring ---
I2C_ID = 0
I2C_SCL_PIN = 17
I2C_SDA_PIN = 16
I2C_FREQ_HZ = 400_000
ADS1115_ADDR = 0x48

# --- ADS1115 channels ---
ADS_FWD_CH = 3
ADS_RFL_CH = 0

# --- ADS1115 measurement settings ---
ADS_PGA = a2d.PGA_4_096V
ADS_DATA_RATE = a2d.DR_860SPS

# --- Pico internal ADC channels ---
VDRAIN_ADC_CH = 0   # ADC0 / GP26
CURRENT_ADC_CH = 1  # ADC1 / GP27
VCC_ADC_CH = 2      # ADC2 / GP28

# --- Scaling ---
VDRAIN_SCALE = 16.6666
VCC_SCALE = 15.05

CURRENT_OFFSET_V = 0.5
CURRENT_V_PER_A  = 0.1

# --- Processing cadence ---
SWR_AVG_WINDOW_MS = 10
PRINT_PERIOD_MS = 500
FAST_TELEM_MS = 10
THERM_TELEM_MS = 500

# --- Calibration files ---
SWR_TABLE_PATH = "swr_table.csv"
THERM_TABLE = "thermistor_calibration.csv"

# --- Protection output ---
PROTECT_GPIO = 14
PROTECT_ACTIVE_HIGH = False

# --- Manual reset input ---
RESET_GPIO = 13
RESET_ACTIVE_LOW = True
RESET_PULL = "UP"
RESET_DEBOUNCE_MS = 10

# --- Protection thresholds ---
PROTECT_VDRAIN_MAX_V = 35.0
PROTECT_IDRAIN_MAX_A = 9
PROTECT_FWD_MIN_FRACTION = 0.1
PROTECT_MIN_I_FOR_EFF_A = 5
PROTECT_MIN_TOTAL_POWER_W = 50.0
PROTECT_TRIP_DEBOUNCE_MS = 200

# --- Thermal protection ---
PROTECT_TEMP_MAX_C = 40.0
PROTECT_THERM_DEBOUNCE_MS = 5000

# --- Thermistor wiring ---
THERM_ADS_CH = 2
THERM_VREF = 3.3
THERM_R_FIXED = 4700.0
THERM_ADS_PGA = ADS_PGA
THERM_ADS_DATA_RATE = ADS_DATA_RATE

# --- Band switching ---
BAND_GPIO_PINS = (4, 5, 6)         
BAND_ACTIVE_HIGH = True        # compatibility for band_switch.py

BAND_BUTTON_GPIO = 7
BAND_BUTTON_ACTIVE_LOW = True
BAND_BUTTON_PULL = "UP"
BAND_BUTTON_DEBOUNCE_MS = 10
BAND_DEFAULT_INDEX = 0

# --- Keyer / PTT ---
KEYER_GPIO = 12                 # <-- set to your PTT/key line
KEYER_ACTIVE_LOW = True         # shorts to GND when keyed
KEYER_PULL = "UP"
KEYER_DEBOUNCE_MS = 10

# --- TX enable output (drives NPN buffer / bias enable / TX relays) ---
TX_EN_GPIO = 15               # <-- choose a free GPIO you wired to your NPN/PNP driver
TX_EN_ACTIVE_HIGH = True      # True: GPIO=1 asserts TX_EN

# --- Display smoothing / peak-hold ---
DISP_HOLD_MS = 600          # how long to freeze the peak
DISP_DECAY_PER_SEC = 0.65   # fraction per second toward live value (0..1), higher=snappier
DISP_WORST_SWR_HOLD = True  # hold worst (max) SWR

# Hold TX_EN on for this long after PTT/key releases (prevents relay chatter on CW)
KEYER_HANG_MS = 200   # typical 150–300ms; start at 200ms



