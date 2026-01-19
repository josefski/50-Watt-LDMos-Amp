# current_sense.py
from machine import ADC

class CurrentSense:
    def __init__(self, adc_channel=1, vref=3.3, offset_v=0.5, v_per_a=0.1):
        self.adc = ADC(adc_channel)
        self.vref = vref
        self.offset_v = offset_v
        self.v_per_a = v_per_a

    def read_adc_raw(self):
        return self.adc.read_u16()

    def read_adc_voltage(self):
        raw = self.read_adc_raw()
        return (raw / 65535.0) * self.vref

    def read_current(self):
        v = self.read_adc_voltage()
        amps = (v - self.offset_v) / self.v_per_a
        if amps < 0.0:
            amps = 0.0
        return amps
