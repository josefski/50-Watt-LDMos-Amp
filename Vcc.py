# Vcc.py
# Vcc measurement module for Raspberry Pi Pico
#
# Reads ADC2 and scales it to actual Vcc using a fixed multiplier.

from machine import ADC

class Vcc:
    def __init__(self, adc_channel=2, vref=3.3, scale=10.0):
        """
        adc_channel: ADC channel number (2 = ADC2 / GP28)
        vref: ADC reference voltage (typically 3.3V on Pico)
        scale: multiplier to convert ADC pin voltage to Vcc
        """
        self.adc = ADC(adc_channel)
        self._K = vref * scale / 65535.0

    def read_vcc_voltage(self):
        """Returns scaled Vcc voltage."""
        return self.adc.read_u16() * self._K
