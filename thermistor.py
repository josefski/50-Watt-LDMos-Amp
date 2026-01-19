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

class PiecewiseLinear:
    def __init__(self, x, y):
        if len(x) != len(y) or len(x) < 2:
            raise ValueError("Interpolator requires >=2 points")
        pairs = sorted(zip(x, y), key=lambda t: t[0])
        self.x = [p[0] for p in pairs]
        self.y = [p[1] for p in pairs]

    def interp(self, xq):
        # Clamp
        if xq <= self.x[0]:
            return self.y[0]
        if xq >= self.x[-1]:
            return self.y[-1]

        for i in range(len(self.x) - 1):
            x0, x1 = self.x[i], self.x[i + 1]
            if x0 <= xq <= x1:
                y0, y1 = self.y[i], self.y[i + 1]
                t = (xq - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)

        return self.y[-1]


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
        self.ads = ads1115
        self.ch = channel
        self.vref = float(vref)
        self.r_fixed = float(r_fixed)
        self.pga = pga
        self.data_rate = data_rate

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
        # Uses your a2d.ADS1115 API
        if self.pga is None and self.data_rate is None:
            return self.ads.read_voltage(channel=self.ch)
        if self.pga is None:
            return self.ads.read_voltage(channel=self.ch, data_rate=self.data_rate)
        if self.data_rate is None:
            return self.ads.read_voltage(channel=self.ch, pga=self.pga)
        return self.ads.read_voltage(channel=self.ch, pga=self.pga, data_rate=self.data_rate)

    def read_temperature_f(self):
        v = self.read_adc_voltage()
        return self.v_to_tf.interp(v)

    def read_temperature_c(self):
        return self.f_to_c(self.read_temperature_f())

    def read_temperature(self):
        # Default for protection logic
        return self.read_temperature_c()
