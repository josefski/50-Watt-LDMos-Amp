# config.py
# Central configuration for Pico HF Amp controller

import a2d

# --- I2C / ADS1115 wiring ---
I2C_ID = 0
I2C_SCL_PIN = 17
I2C_SDA_PIN = 16
I2C_FREQ_HZ = 400_000
ADS1115_ADDR = 0x48

# --- ADS1115 channels (your current wiring) ---
ADS_FWD_CH = 1
ADS_RFL_CH = 0

# --- ADS1115 measurement settings ---
ADS_PGA = a2d.PGA_4_096V
ADS_DATA_RATE = a2d.DR_250SPS

# --- Pico internal ADC channels ---
VDRAIN_ADC_CH = 0   # ADC0 / GP26
CURRENT_ADC_CH = 1  # ADC1 / GP27

# --- Scaling / transfer functions ---
VDRAIN_SCALE = 16.6666

CURRENT_OFFSET_V = 0.5   # volts
CURRENT_V_PER_A  = 0.1   # volts per amp

# --- Processing cadence ---
SWR_AVG_WINDOW_MS = 100
PRINT_PERIOD_MS = 200

# --- Calibration file(s) ---
SWR_TABLE_PATH = "swr_table.csv"

# Pico internal ADC channels
VCC_ADC_CH = 2          # ADC2 / GP28

# Scaling
VCC_SCALE = 15.05

# --- Protection output (drives NPN -> disables P-channel MOSFET rail) ---
PROTECT_GPIO = 14                 # example: GP14
PROTECT_ACTIVE_HIGH = False        # per your design

# --- Manual reset input (button to GND recommended) ---
RESET_GPIO = 13                   # example: GP13
RESET_ACTIVE_LOW = True           # button shorts pin to GND
RESET_PULL = "UP"                 # "UP" or "DOWN" (UP recommended for active-low)
RESET_DEBOUNCE_MS = 10

# --- Trip thresholds ---
PROTECT_VDRAIN_MAX_V = 35.0
PROTECT_IDRAIN_MAX_A = 9
PROTECT_FWD_MIN_FRACTION = 0.25

# --- Guardrails for the "Pfwd too low vs V*I" rule ---
PROTECT_MIN_I_FOR_EFF_A = 2
PROTECT_MIN_TOTAL_POWER_W = 10.0  # only evaluate rule #3 above this

# --- Debounce timing ---
PROTECT_TRIP_DEBOUNCE_MS = 50     # fault must persist this long to trip
RESET_DEBOUNCE_MS = 10            # reset button debounce

# --- Thermistor on ADS1115 ---
THERM_TABLE = "thermistor_calibration.csv"  # your uploaded CSV (Temp_F, Resistance_Ohms)

THERM_ADS_CH = 2            # ADS1115 AIN2 (single-ended to GND)

# Divider constants (3.3V rail -> 4.7k -> ADC node -> thermistor -> GND)
THERM_VREF = 3.3            # top of divider rail
THERM_R_FIXED = 4700.0      # ohms

# ADS settings for thermistor reads
# Use same PGA/DR as other ADS reads unless you want to tune separately
THERM_ADS_PGA = ADS_PGA
THERM_ADS_DATA_RATE = ADS_DATA_RATE

# --- Thermal protection ---
PROTECT_TEMP_MAX_C = 40.0
PROTECT_THERM_DEBOUNCE_MS = 5000   # 5 seconds sustained over-temp to trip

# --- Band switching relays (PNP base drive; active LOW) ---
BAND_GPIO_PINS = (4, 5, 6)     # GP4, GP5, GP6
BAND_ACTIVE_LOW = True         # LOW = relay ON

BAND_BUTTON_GPIO = 7           # GP7 pushbutton
BAND_BUTTON_ACTIVE_LOW = True  # button shorts to GND
BAND_BUTTON_PULL = "UP"        # internal pull-up

BAND_BUTTON_DEBOUNCE_MS = 10   # ms
BAND_DEFAULT_INDEX = 0         # start with first filter selected

# --- Scheduling ---
FAST_TELEM_MS = 10       # vDrain/iDrain/vcc sampling cadence
THERM_TELEM_MS = 500     # temperature sampling cadence (slow is fine)

