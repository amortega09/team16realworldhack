import copy

from config.plant_config import SENSOR_NORMAL_RANGES


EMISSIONS_FACTOR_KG_PER_KWH = 0.233

ACTION_EFFECTS = {
    "adjust_heater_power": {
        "energy_consumption": 2.5,
        "temperature": 0.6,
        "pressure": 0.04,
        "co2": 1.2,
    },
    "adjust_feed_rate": {
        "energy_consumption": 1.8,
        "flow_rate": 1.0,
        "pressure": 0.03,
        "co2": 0.8,
    },
    "adjust_vent_valve": {
        "energy_consumption": 0.3,
        "co2": -4.0,
        "pressure": -0.02,
    },
    "adjust_temperature_setpoint": {
        "energy_consumption": 1.2,
        "temperature": 1.0,
        "pressure": 0.02,
    },
}


def project_state_after_action(state: dict, zone: str, action: str, delta: float) -> dict:
    projected = copy.deepcopy(state)
    zone_state = projected.get(zone)
    if not zone_state:
        return projected

    effects = ACTION_EFFECTS.get(action, {})
    sensors = zone_state.setdefault("sensors", {})
    for sensor, factor in effects.items():
        current = sensors.get(sensor, 0.0)
        sensors[sensor] = round(max(0.0, current + (delta * factor)), 3)

    return projected


def compute_objective_metrics(state: dict, previous_state: dict | None = None, action: str | None = None, delta: float = 0.0) -> dict:
    throughput_score = 0.0
    quality_deviation = 0.0
    stability_penalty = 0.0
    maintenance_risk = 0.0
    co2_total = 0.0
    energy_total = 0.0
    active_zones = 0

    for zone, zone_data in state.items():
        if not zone_data.get("is_working"):
            continue
        active_zones += 1
        sensors = zone_data.get("sensors", {})
        co2_total += sensors.get("co2", 0.0)
        energy_total += sensors.get("energy_consumption", 0.0)

        ranges = SENSOR_NORMAL_RANGES.get(zone, {})
        flow = sensors.get("flow_rate")
        if flow is not None and "flow_rate" in ranges:
            lo, hi = ranges["flow_rate"]
            midpoint = (lo + hi) / 2
            if midpoint:
                throughput_score += max(0.0, 1.0 - abs(flow - midpoint) / midpoint)

        for sensor, bounds in ranges.items():
            current = sensors.get(sensor)
            if current is None:
                continue
            lo, hi = bounds
            midpoint = (lo + hi) / 2
            half_span = max((hi - lo) / 2, 1e-6)
            quality_deviation += abs(current - midpoint) / half_span
            distance_to_limit = min(abs(current - lo), abs(hi - current))
            maintenance_risk += 1.0 / max(distance_to_limit, 1.0)

            if previous_state:
                prev_value = previous_state.get(zone, {}).get("sensors", {}).get(sensor)
                if prev_value is not None:
                    stability_penalty += abs(current - prev_value)

    throughput_score = round(throughput_score / active_zones, 3) if active_zones else 0.0
    co2_emissions = round((energy_total * EMISSIONS_FACTOR_KG_PER_KWH) + (co2_total * 0.0015), 3)
    equipment_wear = round(abs(delta) * _action_wear_multiplier(action), 3)
    recovery_time = round((quality_deviation / max(active_zones, 1)) * 8.0, 3)

    return {
        "co2_emissions": co2_emissions,
        "throughput": throughput_score,
        "product_quality": round(quality_deviation, 3),
        "equipment_wear": equipment_wear,
        "stability": round(stability_penalty, 3),
        "maintenance_risk": round(maintenance_risk, 3),
        "recovery_time": recovery_time,
        "alarm_load": round(quality_deviation * 0.35 + stability_penalty * 0.05, 3),
        "utility_efficiency": round(throughput_score / max(energy_total, 1.0), 5),
        "flaring_or_venting": round(max(0.0, delta) if action == "adjust_vent_valve" else 0.0, 3),
    }


def project_objectives_after_action(state: dict, zone: str, action: str, delta: float, previous_state: dict | None = None) -> dict:
    projected_state = project_state_after_action(state, zone, action, delta)
    return compute_objective_metrics(projected_state, previous_state=previous_state, action=action, delta=delta)


def _action_wear_multiplier(action: str | None) -> float:
    multipliers = {
        "adjust_heater_power": 0.8,
        "adjust_feed_rate": 0.6,
        "adjust_vent_valve": 1.1,
        "adjust_temperature_setpoint": 0.5,
    }
    return multipliers.get(action, 0.4)
