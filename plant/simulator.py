from .loader import load_hierarchy, load_metrics


class PlantSimulator:
    def __init__(self):
        self.zones      = load_hierarchy()
        self.metrics, self.hour_meta, self.start_dt = load_metrics()
        self.geom_to_zone = {z['geometry_id']: name for name, z in self.zones.items()}
        self.total_hours  = max(self.metrics.keys()) + 1
        self.current_hour = 0
        self.overrides    = {}  # {zone: {metric: cumulative_delta}}
        self.paused       = False

    def get_current_state(self):
        """Returns current sensor readings for all zones."""
        hour_data  = self.metrics.get(self.current_hour, {})
        is_working = self.hour_meta.get(self.current_hour, True)
        state = {}

        for zone_name, zone_info in self.zones.items():
            geom_id     = zone_info['geometry_id']
            sensor_data = hour_data.get(geom_id, {})
            sensors = {}

            for metric, aggs in sensor_data.items():
                base  = aggs.get('mean', 0.0)
                delta = self.overrides.get(zone_name, {}).get(metric, 0.0)
                sensors[metric] = round(base + delta, 3)

            state[zone_name] = {
                'display_name': zone_info['display_name'],
                'sensors':      sensors,
                'is_working':   is_working,
            }

        return state

    def apply_override(self, zone: str, metric: str, delta: float):
        """Accumulate a control agent adjustment on top of CSV base values."""
        self.overrides.setdefault(zone, {})[metric] = (
            self.overrides.get(zone, {}).get(metric, 0.0) + delta
        )

    def advance(self):
        if not self.paused:
            self.current_hour = min(self.current_hour + 1, self.total_hours - 1)

    def reset(self):
        self.current_hour = 0
        self.overrides    = {}

    @property
    def finished(self):
        return self.current_hour >= self.total_hours - 1
