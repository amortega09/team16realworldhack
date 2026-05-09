# Hard absolute limits for sensor readings — control actions that would push
# a value outside these bounds are rejected regardless of Supervisor intent.

HARD_LIMITS = {
    "r101": {
        "temperature":        (55,   250),
        "pressure":           (0.5,  8.0),
        "co2":                (0,   1200),
        "flow_rate":          (20,   160),
        "ph":                 (4.5,  9.5),
        "energy_consumption": (0,    400),
    },
    "r102": {
        "temperature":        (50,   240),
        "pressure":           (0.5,  7.5),
        "co2":                (0,   1100),
        "flow_rate":          (15,   155),
        "ph":                 (4.5,  9.5),
        "energy_consumption": (0,    360),
    },
    "hx01": {
        "temperature":        (20,    90),
        "pressure":           (0.2,  4.5),
        "flow_rate":          (30,   520),
        "energy_consumption": (0,    130),
    },
    "dist-c01": {
        "temperature":        (40,   165),
        "pressure":           (0.1,  3.8),
        "flow_rate":          (10,   130),
        "energy_consumption": (0,    420),
    },
    "util": {
        "temperature":        (60,   200),
        "pressure":           (1.0, 10.0),
        "flow_rate":          (80,  1150),
        "energy_consumption": (0,    280),
    },
}

# Control action rate limits: max magnitude of delta per single call
ACTION_RATE_LIMITS = {
    "adjust_temperature_setpoint": 5.0,   # °C per call
    "adjust_feed_rate":            15.0,  # % of nominal per call
    "adjust_vent_valve":           25.0,  # % open per call
    "adjust_heater_power":         20.0,  # % of rated per call
}

# Which sensor each action primarily affects (for projected-value safety check)
ACTION_SENSOR_MAP = {
    "adjust_temperature_setpoint": "temperature",
    "adjust_feed_rate":            "flow_rate",
    "adjust_vent_valve":           "co2",
    "adjust_heater_power":         "energy_consumption",
}


def check_action(zone: str, action: str, delta: float, current_value: float) -> dict:
    """
    Validate a proposed control action.
    Returns {"ok": True} or {"ok": False, "reason": str, "safe_max_delta": float}
    """
    rate_limit = ACTION_RATE_LIMITS.get(action)
    if rate_limit and abs(delta) > rate_limit:
        capped = rate_limit * (1 if delta > 0 else -1)
        return {
            "ok": False,
            "reason": f"Delta {delta:+.1f} exceeds rate limit ±{rate_limit}",
            "safe_max_delta": capped,
        }

    sensor  = ACTION_SENSOR_MAP.get(action)
    limits  = HARD_LIMITS.get(zone, {}).get(sensor) if sensor else None
    if limits:
        projected = current_value + delta
        lo, hi    = limits
        if projected < lo:
            return {
                "ok": False,
                "reason": f"Projected {sensor} {projected:.2f} would breach hard minimum {lo}",
                "safe_max_delta": lo - current_value,
            }
        if projected > hi:
            return {
                "ok": False,
                "reason": f"Projected {sensor} {projected:.2f} would breach hard maximum {hi}",
                "safe_max_delta": hi - current_value,
            }

    return {"ok": True}
