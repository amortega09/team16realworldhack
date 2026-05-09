from plant.safety_envelope import check_action, ACTION_SENSOR_MAP
from plant.cost_model import compute_cost_per_hour, project_cost_after_action


class ControlAgent:
    def __init__(self, simulator):
        self._sim = simulator

    def execute(self, zone: str, action: str, delta: float, reason: str) -> dict:
        state         = self._sim.get_current_state()
        sensor        = ACTION_SENSOR_MAP.get(action)
        current_value = state.get(zone, {}).get('sensors', {}).get(sensor, 0.0) if sensor else 0.0
        cost_before   = compute_cost_per_hour(state)

        validation = check_action(zone, action, delta, current_value)

        if not validation["ok"]:
            return {
                "status":     "rejected",
                "zone":       zone,
                "action":     action,
                "delta":      delta,
                "reason":     validation["reason"],
                "safe_max":   validation.get("safe_max_delta"),
                "cost_before": cost_before,
                "cost_after":  cost_before,
                "saving":      0.0,
            }

        # Apply the override to the simulator
        if sensor:
            self._sim.apply_override(zone, sensor, delta)

        cost_after = project_cost_after_action(state, zone, action, delta)
        saving     = round(cost_before - cost_after, 2)

        return {
            "status":      "executed",
            "zone":        zone,
            "action":      action,
            "delta":       delta,
            "reason":      reason,
            "cost_before": cost_before,
            "cost_after":  cost_after,
            "saving":      saving,
        }
