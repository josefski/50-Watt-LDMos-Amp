# thermistor.py
#
# Thermistor on ADS1115 AINx using divider:
#   VREF (3.3V) --- R_FIXED (4.7k) --- ADC_NODE --- NTC --- GND
#
# Divider voltage:
#   Vadc = Vref * (R_ntc / (R_fixed + R_ntc))
#
# Your CSV is two-row format:
#   Temperature,<F values...>
#   Resistance,<ohms values...>
#
# We:
#   1) load (Temp_F, R_ohms) pairs
#   2) compute expected Vadc for each R
#   3) build interpolator Vadc -> Temp_F
#   4) convert to Celsius for protection

from interp import PiecewiseLinear


def _to_floats(parts):
    out = []
    for p in parts:
        try:
            out.append(float(p.strip()))
        except:
            # ignore non-numeric cells
            pass
    return out


def load_two_row_table(csv_path):
    """
    Loads your two-row CSV:
      Temperature,<F values...>
      Resistance,<ohms values...>

    Returns: (temps_f_list, resistances_ohms_list)
    """
    with open(csv_path, "r") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    if len(lines) < 2:
        raise ValueError("Thermistor CSV must contain at least 2 non-empty rows")

    temp_parts = [p.strip() for p in lines[0].split(",")]
    res_parts  = [p.strip() for p in lines[1].split(",")]

    temps_f = _to_floats(temp_parts[1:])      # skip label cell
    res_ohm = _to_floats(res_parts[1:])       # skip label cell

    if len(temps_f) < 2 or len(res_ohm) < 2:
        raise ValueError("Thermistor CSV does not contain enough numeric points")

    if len(temps_f) != len(res_ohm):
        raise ValueError("Thermistor CSV temperature and resistance lists are different lengths")

    return temps_f, res_ohm


def resistance_to_vadc(r_ntc, vref, r_fixed):
    # Vadc = Vref * (Rntc / (Rfixed + Rntc))
    return vref * (r_ntc / (r_fixed + r_ntc))


class ThermistorADS:
    def __init__(self, ads1115, channel, csv_path,
                 vref=3.3, r_fixed=4700.0, pga=None, data_rate=None):
        from a2d import PGA_4_096V, DR_250SPS
        self.ads = ads1115
        self.ch = channel
        self.vref = float(vref)
        self.r_fixed = float(r_fixed)
        self.pga = pga if pga is not None else PGA_4_096V
        self.data_rate = data_rate if data_rate is not None else DR_250SPS

        # Load measured table (Temp_F, R)
        temps_f, res_ohm = load_two_row_table(csv_path)

        # Compute expected divider voltage for each resistance
        vadc = [resistance_to_vadc(r, self.vref, self.r_fixed) for r in res_ohm]

        # Build interpolator: Vadc -> Temp_F
        self.v_to_tf = PiecewiseLinear(vadc, temps_f)

    @staticmethod
    def f_to_c(tf):
        return (tf - 32.0) * (5.0 / 9.0)

    def read_adc_voltage(self):
        return self.ads.read_voltage(channel=self.ch, pga=self.pga, data_rate=self.data_rate)

    def read_temperature_f(self):
        v = self.read_adc_voltage()
        return self.v_to_tf.interp(v)

    def read_temperature_c(self):
        return self.f_to_c(self.read_temperature_f())

    def read_temperature(self):
        # Default for protection logic
        return self.read_temperature_c()
