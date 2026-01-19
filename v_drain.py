# v_drain.py
from machine import ADC

class VDrain:
    def __init__(self, adc_channel=0, vref=3.3, scale=16.6666):
        self.adc = ADC(adc_channel)
        self.vref = vref
        self.scale = scale

    def read_adc_raw(self):
        return self.adc.read_u16()

    def read_adc_voltage(self):
        raw = self.read_adc_raw()
        return (raw / 65535.0) * self.vref

    def read_drain_voltage(self):
        return self.read_adc_voltage() * self.scale
