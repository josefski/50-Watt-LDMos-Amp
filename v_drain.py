# v_drain.py
from machine import ADC

class VDrain:
    def __init__(self, adc_channel=0, vref=3.3, scale=16.6666):
        self.adc = ADC(adc_channel)
        self._K = vref * scale / 65535.0

    def read_drain_voltage(self):
        return self.adc.read_u16() * self._K
