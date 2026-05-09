ELECTRICITY_RATE_GBP_PER_KWH = 0.15  # £/kWh (UK industrial rate)


def compute_cost_per_hour(state: dict) -> float:
    """Sum energy_consumption across all working zones → £/hr."""
    total_kw = 0.0
    for zone_data in state.values():
        if zone_data.get('is_working'):
            total_kw += zone_data['sensors'].get('energy_consumption', 0.0)
    return round(total_kw * ELECTRICITY_RATE_GBP_PER_KWH, 2)


def project_cost_after_action(state: dict, zone: str, action: str, delta: float) -> float:
    """Estimate cost/hr after a proposed action using simplified sensor relationships."""
    # Copy current energy values and apply the delta's estimated energy effect
    import copy
    projected = copy.deepcopy(state)

    # Simplified model: heater power and feed rate directly scale energy_consumption
    energy_deltas = {
        "adjust_heater_power": delta * 2.5,   # 1% heater ≈ 2.5 kW
        "adjust_feed_rate":    delta * 1.8,   # 1% feed  ≈ 1.8 kW
        "adjust_vent_valve":   delta * 0.3,   # minimal energy effect
        "adjust_temperature_setpoint": delta * 1.2,
    }
    energy_delta = energy_deltas.get(action, 0.0)
    if zone in projected:
        current_e = projected[zone]['sensors'].get('energy_consumption', 0.0)
        projected[zone]['sensors']['energy_consumption'] = max(0, current_e + energy_delta)

    return compute_cost_per_hour(projected)
