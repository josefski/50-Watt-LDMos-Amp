# Configuration for 16x2 LCD Display

# I2C address for the 16x2 LCD
LCD_I2C_ADDR = 0x27

# Dimensions of the display
LCD_COLS = 16
LCD_ROWS = 2

# LCD refresh interval in milliseconds
LCD_REFRESH_MS = 250

# Band labels for display (40m, 20m, 10m)
BAND_LABELS = ["40", "20", "10"]

# Line templates for 16x2 layout
# Line 0: SWR, Forward Power, Band
# Format: "S:1.2 P:50 40"
LINE0 = "S:{swr} P:{pfwd} {band}"

# Line 1: Drain Voltage, Current
# Format: "D:28.5V I:3.2A"
LINE1 = "D:{vd}V I:{id}A"
