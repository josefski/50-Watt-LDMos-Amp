# lcd_i2c.py
# Minimal HD44780 (20x4) via PCF8574 I2C backpack driver for MicroPython (RP2040)
#
# Wiring:
#   SDA = GP2
#   SCL = GP3
#
# Typical backpack I2C addresses: 0x27 or 0x3F

import utime
from machine import I2C, Pin

# PCF8574 pin mapping commonly used on I2C LCD backpacks:
# P0=RS, P1=RW, P2=E, P3=Backlight, P4..P7 = D4..D7
_MASK_RS = 0x01
_MASK_RW = 0x02
_MASK_E  = 0x04
_MASK_BL = 0x08


class LCD2004:
    def __init__(self, i2c: I2C, addr: int = 0x27, backlight: bool = True):
        self.i2c = i2c
        self.addr = addr
        self.backlight = backlight
        self._bl = _MASK_BL if backlight else 0x00
        self._init_lcd()

    # ---------- Low-level I2C write ----------
    def _write_byte(self, data: int):
        self.i2c.writeto(self.addr, bytes([data]))

    # ---------- 4-bit bus helpers ----------
    def _pulse_enable(self, data: int):
        # Enable high -> low pulse to latch nibble
        self._write_byte(data | _MASK_E)
        utime.sleep_us(1)
        self._write_byte(data & ~_MASK_E)
        utime.sleep_us(50)

    def _write4(self, nibble: int, rs: int):
        # nibble is upper 4 bits already positioned (bits 4..7)
        data = nibble | self._bl | ( _MASK_RS if rs else 0x00 )
        self._write_byte(data)
        self._pulse_enable(data)

    def _send(self, value: int, rs: int):
        # Send high nibble then low nibble
        hi = (value & 0xF0)
        lo = ((value << 4) & 0xF0)
        self._write4(hi, rs)
        self._write4(lo, rs)

    def command(self, cmd: int):
        self._send(cmd, rs=0)

    def write_char(self, ch: str):
        self._send(ord(ch), rs=1)

    # ---------- LCD init / control ----------
    def _init_lcd(self):
        # HD44780 initialization sequence for 4-bit mode
        utime.sleep_ms(50)

        # Force into 8-bit mode first (send 0x30 three times as high nibble)
        self._write4(0x30, rs=0)
        utime.sleep_ms(5)
        self._write4(0x30, rs=0)
        utime.sleep_us(150)
        self._write4(0x30, rs=0)
        utime.sleep_us(150)

        # Set to 4-bit mode (0x20 high nibble)
        self._write4(0x20, rs=0)
        utime.sleep_us(150)

        # Function set: 4-bit, 2-line (works for 20x4), 5x8 font
        self.command(0x28)

        # Display on, cursor off, blink off
        self.command(0x0C)

        # Entry mode set: increment, no shift
        self.command(0x06)

        self.clear()

    def clear(self):
        self.command(0x01)
        utime.sleep_ms(2)

    def home(self):
        self.command(0x02)
        utime.sleep_ms(2)

    # ---------- Positioning ----------
    def set_cursor(self, col: int, row: int):
        # 20x4 DDRAM addresses:
        # Row0: 0x00, Row1: 0x40, Row2: 0x14, Row3: 0x54
        row_offsets = [0x00, 0x40, 0x14, 0x54]
        if row < 0:
            row = 0
        if row > 3:
            row = 3
        if col < 0:
            col = 0
        if col > 19:
            col = 19
        addr = 0x80 | (row_offsets[row] + col)
        self.command(addr)

    def write(self, text: str):
        for ch in text:
            self.write_char(ch)

    def write_line(self, row: int, text: str):
        # Writes and pads/truncates to 20 chars
        s = (text + " " * 20)[:20]
        self.set_cursor(0, row)
        self.write(s)


def make_i2c_gp2_gp3(freq=100_000) -> I2C:
    # GP2= SDA, GP3= SCL => typically I2C(1) on Pico
    return I2C(1, sda=Pin(2), scl=Pin(3), freq=freq)
