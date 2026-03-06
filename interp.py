# interp.py
# Shared piecewise-linear interpolator used by swr_calc and thermistor.

import bisect


class PiecewiseLinear:
    def __init__(self, x, y):
        if len(x) != len(y) or len(x) < 2:
            raise ValueError("Need >=2 points with matching x/y lengths")
        pairs = sorted(zip(x, y), key=lambda t: t[0])
        self.x = [p[0] for p in pairs]
        self.y = [p[1] for p in pairs]

    def interp(self, xq):
        x = self.x
        y = self.y
        if xq <= x[0]:
            return y[0]
        if xq >= x[-1]:
            return y[-1]
        i = bisect.bisect_right(x, xq) - 1
        x0, x1 = x[i], x[i + 1]
        if x1 == x0:
            return y[i]
        t = (xq - x0) / (x1 - x0)
        return y[i] + t * (y[i + 1] - y[i])
