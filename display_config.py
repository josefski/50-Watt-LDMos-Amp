# display_config.py
# LCD display configuration (16x2 over I2C backpack)

# Hardware
LCD_I2C_ADDR = 0x27
LCD_COLS = 16
LCD_ROWS = 2

# Display refresh cadence (ms)
LCD_REFRESH_MS = 250

# Formatting behavior
# If SWR is infinite or invalid, display as "inf"
SWR_INF_TEXT = "inf"

# Band labels (displayed for each one-hot band index 0..2)
BAND_LABELS = ("10", "20", "40")

# Line templates for 16 chars:
# Keys used in templates:
#   swr  - 2-char SWR integer ("--" when no RF)
#   pfwd - 2-char forward power integer (W)
#   ia   - 2-char drain current (1 decimal, A)
#   vd   - 2-char drain voltage (1 decimal, V)
#   band - band label ("40"/"20"/"10")
LINE0 = "S:{swr} P:{pfwd}W{band}"
LINE1 = "I:{ia}A D:{vd}V"
