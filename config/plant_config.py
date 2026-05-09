ZONES = {
    "r101":     "Reactor R-101",
    "r102":     "Reactor R-102",
    "hx01":     "Heat Exchanger HX-01",
    "dist-c01": "Distillation Column C-01",
    "util":     "Utility Zone",
}

SENSOR_UNITS = {
    "temperature":        "°C",
    "pressure":           "bar",
    "co2":                "ppm",
    "flow_rate":          "L/min",
    "ph":                 "pH",
    "energy_consumption": "kW",
}

SENSOR_NORMAL_RANGES = {
    "r101": {
        "temperature":        (160, 200),
        "pressure":           (3.0, 5.5),
        "co2":                (250, 480),
        "flow_rate":          (85,  110),
        "ph":                 (6.9, 7.4),
        "energy_consumption": (180, 230),
    },
    "r102": {
        "temperature":        (155, 195),
        "pressure":           (2.8, 5.2),
        "co2":                (230, 460),
        "flow_rate":          (80,  105),
        "ph":                 (7.0, 7.5),
        "energy_consumption": (165, 215),
    },
    "hx01": {
        "temperature":        (48,  62),
        "pressure":           (1.2, 2.8),
        "flow_rate":          (200, 350),
        "energy_consumption": (45,  85),
    },
    "dist-c01": {
        "temperature":        (95,  125),
        "pressure":           (0.8, 2.2),
        "flow_rate":          (60,  90),
        "energy_consumption": (220, 290),
    },
    "util": {
        "temperature":        (135, 165),
        "pressure":           (4.0, 7.0),
        "flow_rate":          (500, 800),
        "energy_consumption": (120, 180),
    },
}
