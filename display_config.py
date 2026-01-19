# display_config.py
# LCD display configuration (20x4 over I2C backpack)

# Hardware
LCD_I2C_ADDR = 0x27
LCD_COLS = 20
LCD_ROWS = 4

# Display refresh cadence (ms)
LCD_REFRESH_MS = 250

# Formatting behavior
# If SWR is infinite or invalid, display as "inf"
SWR_INF_TEXT = "inf"

# Line templates (20 chars max; display.py will pad/truncate safely)
# Keys expected in telemetry/state:
#   latest: pfwd_w, swr, vDrain, iDrain, temp_c
#   state:  amp_enabled, tripped, reason
LINE0 = "PFWD:{pfwd:>5}W SWR:{swr:>4}"
LINE1 = "VD:{vd:>5}V ID:{id:>4}A"
LINE2 = "T:{tc:>5}C"
# LINE3 is status; display.py chooses content based on fault/amp state
STATUS_OK_ON  = "AMP ON"
STATUS_OK_OFF = "AMP OFF"
STATUS_FAULT_PREFIX = "FAULT:"

