from plant.safety_envelope import check_action, ACTION_SENSOR_MAP
from plant.cost_model import compute_cost_per_hour, project_cost_after_action
from plant.objective_model import compute_objective_metrics, project_objectives_after_action


class ControlAgent:
    def __init__(self, simulator):
        self._sim = simulator

    def execute(self, zone: str, action: str, delta: float, reason: str) -> dict:
        state         = self._sim.get_current_state()
        sensor        = ACTION_SENSOR_MAP.get(action)
        current_value = state.get(zone, {}).get('sensors', {}).get(sensor, 0.0) if sensor else 0.0
        cost_before   = compute_cost_per_hour(state)
        objectives_before = compute_objective_metrics(state)

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
                "objectives_before": objectives_before,
                "objectives_after": objectives_before,
            }

        # Apply the override to the simulator
        if sensor:
            self._sim.apply_override(zone, sensor, delta)

        cost_after = project_cost_after_action(state, zone, action, delta)
        objectives_after = project_objectives_after_action(state, zone, action, delta, previous_state=state)
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
            "objectives_before": objectives_before,
            "objectives_after": objectives_after,
        }
