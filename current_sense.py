# current_sense.py
from machine import ADC

class CurrentSense:
    def __init__(self, adc_channel=1, vref=3.3, offset_v=0.5, v_per_a=0.1):
        self.adc = ADC(adc_channel)
        self._K = vref / (65535.0 * v_per_a)
        self._offset = offset_v / v_per_a

    def read_current(self):
        amps = self.adc.read_u16() * self._K - self._offset
        return amps if amps > 0.0 else 0.0
