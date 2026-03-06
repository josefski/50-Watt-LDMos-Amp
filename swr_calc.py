# swr_calc.py
import math
from interp import PiecewiseLinear
from a2d import _DR_SPS

def _try_float(s):
    try:
        return float(s.strip())
    except:
        return None

def load_v_to_w_curve(csv_path):
    # CSV is Power_W, Voltage_V (header likely "FWD,V")
    power_w = []
    volts_v = []
    with open(csv_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                continue
            p = _try_float(parts[0])
            v = _try_float(parts[1])
            if p is None or v is None:
                continue
            power_w.append(p)
            volts_v.append(v)

    if len(power_w) < 2:
        raise ValueError("Calibration table has insufficient numeric rows")

    # invert: V -> W
    return PiecewiseLinear(volts_v, power_w)

def swr_from_powers(pfwd_w, prfl_w):
    if pfwd_w <= 0.0:
        return float("inf")
    if prfl_w < 0.0:
        prfl_w = 0.0
    ratio = prfl_w / pfwd_w
    if ratio >= 1.0:
        return float("inf")
    gamma = math.sqrt(ratio)
    denom = 1.0 - gamma
    if denom <= 0.0:
        return float("inf")
    return (1.0 + gamma) / denom

class SWRCalc:
    def __init__(self, ads1115, fwd_channel, rfl_channel, pga, data_rate, table_path):
        self.ads = ads1115
        self.fwd_ch = fwd_channel
        self.rfl_ch = rfl_channel
        self.pga = pga
        self.data_rate = data_rate
        self.v_to_w = load_v_to_w_curve(table_path)

    def read_avg_volts(self, window_ms=100):
        # Deterministic sample count derived from ADS1115 SPS
        sps = _DR_SPS.get(self.data_rate, 128)
        samples = int((sps * window_ms) / 1000)
        if samples < 1:
            samples = 1

        sum_fwd = 0.0
        sum_rfl = 0.0
        for _ in range(samples):
            sum_fwd += self.ads.read_voltage(self.fwd_ch, pga=self.pga, data_rate=self.data_rate)
            sum_rfl += self.ads.read_voltage(self.rfl_ch, pga=self.pga, data_rate=self.data_rate)

        return (sum_fwd / samples), (sum_rfl / samples), samples

    def compute(self, window_ms=100):
        vfwd_v, vrfl_v, n = self.read_avg_volts(window_ms=window_ms)

        pfwd_w = self.v_to_w.interp(vfwd_v)
        prfl_w = self.v_to_w.interp(vrfl_v)

        if pfwd_w < 0.0: pfwd_w = 0.0
        if prfl_w < 0.0: prfl_w = 0.0

        swr = swr_from_powers(pfwd_w, prfl_w)
        pdel_w = pfwd_w - prfl_w
        if pdel_w < 0.0:
            pdel_w = 0.0

        return {
            "vfwd_v": vfwd_v,
            "vrfl_v": vrfl_v,
            "pfwd_w": pfwd_w,
            "prfl_w": prfl_w,
            "pdel_w": pdel_w,
            "swr": swr,
            "samples": n,
        }
