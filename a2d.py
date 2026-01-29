# a2d.py
# Minimal ADS1115 driver and constants for MicroPython used by the HF amplifier controller
# Provides: ADS1115 class with probe(), read_voltage(channel, pga=None, data_rate=None)
# and constants for PGA and Data Rate matching usage in the repo.

import utime

# ADS1115 registers
_CONVERSION_REG = 0x00
_CONFIG_REG = 0x01

# PGA (full-scale) configuration bits (config register bits 11:9)
PGA_6_144V = 0x0000
PGA_4_096V = 0x0200
PGA_2_048V = 0x0400
PGA_1_024V = 0x0600
PGA_0_512V = 0x0800
PGA_0_256V = 0x0A00

# Data rate configuration bits (config register bits 7:5)
DR_8SPS   = 0x0000
DR_16SPS  = 0x0020
DR_32SPS  = 0x0040
DR_64SPS  = 0x0060
DR_128SPS = 0x0080
DR_250SPS = 0x00A0
DR_475SPS = 0x00C0
DR_860SPS = 0x00E0

# Convenience mapping from DR code -> samples/sec (used internally to wait for conversion)
_DR_SPS = {
    DR_8SPS: 8,
    DR_16SPS: 16,
    DR_32SPS: 32,
    DR_64SPS: 64,
    DR_128SPS: 128,
    DR_250SPS: 250,
    DR_475SPS: 475,
    DR_860SPS: 860,
}

# Map PGA bits to full-scale voltage
_PGA_FS_V = {
    PGA_6_144V: 6.144,
    PGA_4_096V: 4.096,
    PGA_2_048V: 2.048,
    PGA_1_024V: 1.024,
    PGA_0_512V: 0.512,
    PGA_0_256V: 0.256,
}

class ADS1115:
    """
    Minimal ADS1115 wrapper compatible with usage elsewhere in this repository.

    Usage:
      ads = ADS1115(i2c, address=0x48)
      ads.probe()  # returns True if device responds on I2C
      v = ads.read_voltage(channel=0, pga=PGA_4_096V, data_rate=DR_250SPS)

    Notes:
    - This implementation performs single-shot conversions for single-ended channels 0..3.
    - It attempts to be conservative about timing by waiting one conversion period + small margin.
    - It uses the standard ADS1115 config register layout and disables the comparator by setting COMP_QUE = 0b11.
    """

    def __init__(self, i2c, address=0x48):
        self.i2c = i2c
        self.address = address

    def probe(self):
        """Return True if the device responds to a config register read."""
        try:
            # Try to read two bytes from the config register
            self.i2c.readfrom_mem(self.address, _CONFIG_REG, 2)
            return True
        except Exception:
            return False

    def _write_config(self, cfg):
        # cfg is a 16-bit integer, write big-endian
        hi = (cfg >> 8) & 0xFF
        lo = cfg & 0xFF
        self.i2c.writeto_mem(self.address, _CONFIG_REG, bytes([hi, lo]))

    def _read_conversion_raw(self):
        data = self.i2c.readfrom_mem(self.address, _CONVERSION_REG, 2)
        hi, lo = data[0], data[1]
        raw = (hi << 8) | lo
        # signed 16-bit
        if raw & 0x8000:
            raw -= 1 << 16
        return raw

    def read_raw(self, channel=0, pga=PGA_4_096V, data_rate=DR_250SPS):
        """Perform a single-shot conversion and return raw int16 reading."""
        if channel not in (0, 1, 2, 3):
            raise ValueError("ADS channel must be 0..3")

        # MUX for single-ended: 100 (AIN0), 101 (AIN1), 110 (AIN2), 111 (AIN3)
        mux = 0x4000 | (channel << 12)

        # OS = 1 (start single conversion)
        os = 0x8000
        # Mode = single-shot (bit = 1 << 8)
        mode_single = 0x0100
        # Comparator disable (COMP_QUE = 0b11)
        comp_disable = 0x0003

        cfg = os | mux | pga | mode_single | data_rate | comp_disable

        # Write config to start conversion
        self._write_config(cfg)

        # Wait for conversion to complete: 1/sps plus small margin
        sps = _DR_SPS.get(data_rate, 128)
        wait_ms = int(1000.0 / float(sps)) + 2
        utime.sleep_ms(wait_ms)

        raw = self._read_conversion_raw()
        return raw

    def read_voltage(self, channel=0, pga=PGA_4_096V, data_rate=DR_250SPS):
        """Return voltage in volts for the given single-ended channel."""
        raw = self.read_raw(channel=channel, pga=pga, data_rate=data_rate)
        fs = _PGA_FS_V.get(pga, 4.096)
        # ADS1115 is signed 16-bit, full-scale corresponds to +/- FS
        # LSB = FS / 32768
        volts = (raw * fs) / 32768.0
        return volts

