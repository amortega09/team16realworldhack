from collections import deque
import numpy as np
from config.thresholds import THRESHOLDS, SPIKE_THRESHOLDS, TREND_WINDOW, TREND_MINUTES_WARN, TREND_MINUTES_CRIT


class MonitorAgent:
    def __init__(self):
        # Rolling history per (zone, sensor): deque of float values
        self._history: dict[tuple, deque] = {}

    def check(self, state: dict) -> list[dict]:
        alerts = []
        for zone, zone_data in state.items():
            if not zone_data.get('is_working'):
                continue
            thresholds = THRESHOLDS.get(zone, {})
            for sensor, value in zone_data['sensors'].items():
                key = (zone, sensor)
                if key not in self._history:
                    self._history[key] = deque(maxlen=TREND_WINDOW)
                self._history[key].append(value)

                limits = thresholds.get(sensor)
                if not limits:
                    continue

                lo_warn, lo_crit, hi_warn, hi_crit = limits

                # 1. Threshold breach
                breach = self._check_breach(zone, sensor, value, lo_warn, lo_crit, hi_warn, hi_crit)
                if breach:
                    alerts.append(breach)
                    continue  # breach supersedes trend/spike for same sensor

                # 2. Trend (linear regression predicting future breach)
                trend = self._check_trend(zone, sensor, value, list(self._history[key]),
                                          lo_warn, lo_crit, hi_warn, hi_crit)
                if trend:
                    alerts.append(trend)
                    continue

                # 3. Rate-of-change spike
                spike = self._check_spike(zone, sensor, value, list(self._history[key]))
                if spike:
                    alerts.append(spike)

        return alerts

    def _check_breach(self, zone, sensor, value, lo_warn, lo_crit, hi_warn, hi_crit):
        if lo_crit is not None and value <= lo_crit:
            return self._alert(zone, sensor, value, lo_crit, "breach", "critical")
        if hi_crit is not None and value >= hi_crit:
            return self._alert(zone, sensor, value, hi_crit, "breach", "critical")
        if lo_warn is not None and value <= lo_warn:
            return self._alert(zone, sensor, value, lo_warn, "breach", "warning")
        if hi_warn is not None and value >= hi_warn:
            return self._alert(zone, sensor, value, hi_warn, "breach", "warning")
        return None

    def _check_trend(self, zone, sensor, value, history, lo_warn, lo_crit, hi_warn, hi_crit):
        if len(history) < 3:
            return None

        x = np.arange(len(history), dtype=float)
        y = np.array(history, dtype=float)
        slope = float(np.polyfit(x, y, 1)[0])  # units/hour

        if abs(slope) < 1e-6:
            return None

        def minutes_to(limit):
            if limit is None or slope == 0:
                return None
            gap = limit - value
            if (gap > 0 and slope > 0) or (gap < 0 and slope < 0):
                return (gap / slope) * 60
            return None

        for limit, severity in [
            (hi_crit, "critical"), (lo_crit, "critical"),
            (hi_warn, "warning"),  (lo_warn, "warning"),
        ]:
            mins = minutes_to(limit)
            if mins is not None and 0 < mins <= TREND_MINUTES_WARN:
                sev = "critical" if mins <= TREND_MINUTES_CRIT else severity
                alert = self._alert(zone, sensor, value, limit, "trend", sev)
                alert["minutes_to_breach"] = round(mins, 1)
                alert["trend_slope"] = round(slope, 3)
                return alert

        return None

    def _check_spike(self, zone, sensor, value, history):
        if len(history) < 2:
            return None
        delta = abs(history[-1] - history[-2])
        spike_limit = SPIKE_THRESHOLDS.get(sensor)
        if spike_limit and delta > spike_limit:
            alert = self._alert(zone, sensor, value, spike_limit, "spike", "warning")
            alert["rate_of_change"] = round(history[-1] - history[-2], 3)
            return alert
        return None

    @staticmethod
    def _alert(zone, sensor, value, threshold, alert_type, severity):
        return {
            "zone":              zone,
            "sensor":            sensor,
            "value":             round(value, 3),
            "threshold":         threshold,
            "type":              alert_type,
            "severity":          severity,
            "minutes_to_breach": None,
            "trend_slope":       None,
            "rate_of_change":    None,
        }
