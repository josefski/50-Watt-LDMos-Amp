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
BAND_LABELS = ("40", "20", "10")

# Line templates for 16 chars:
# Keys used in templates:
#   swr - 4-char SWR string
#   pfwd - 4-char forward power (integer)
#   id - 4-char current (1 decimal)
#   vd - 4-char drain voltage (1 decimal)
#   band - band label ("40"/"20"/"10")
LINE0 = "S:{swr} P:{pfwd}W B:{band}"
LINE1 = "I:{id}A D:{vd}V"
