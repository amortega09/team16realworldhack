# Alert thresholds: (low_warning, low_critical, high_warning, high_critical)
# None means that direction has no threshold for that sensor in that zone

THRESHOLDS = {
    "r101": {
        "temperature":        (None, None,  220,  240),
        "pressure":           (1.5,  1.0,   6.5,  8.0),
        "co2":                (None, None,  680,  900),
        "flow_rate":          (50,   30,    140,  160),
        "ph":                 (6.1,  5.5,   8.2,  9.0),
        "energy_consumption": (None, None,  300,  380),
    },
    "r102": {
        "temperature":        (None, None,  215,  235),
        "pressure":           (1.5,  1.0,   6.2,  7.5),
        "co2":                (None, None,  650,  850),
        "flow_rate":          (45,   25,    135,  155),
        "ph":                 (6.2,  5.5,   8.3,  9.0),
        "energy_consumption": (None, None,  280,  350),
    },
    "hx01": {
        "temperature":        (None, None,   75,   90),
        "pressure":           (0.5,  0.3,    3.5,  4.5),
        "flow_rate":          (100,  60,     480,  520),
        "energy_consumption": (None, None,   110,  130),
    },
    "dist-c01": {
        "temperature":        (None, None,  148,  165),
        "pressure":           (0.3,  0.2,    3.0,  3.8),
        "flow_rate":          (25,   15,    115,  130),
        "energy_consumption": (None, None,  360,  420),
    },
    "util": {
        "temperature":        (None, None,  180,  200),
        "pressure":           (2.5,  1.5,    8.5, 10.0),
        "flow_rate":          (200,  120,   1050, 1150),
        "energy_consumption": (None, None,   240,  280),
    },
}

# Rate-of-change spike thresholds (max allowed delta between consecutive hourly readings)
SPIKE_THRESHOLDS = {
    "temperature":        15.0,
    "pressure":           1.5,
    "co2":                150.0,
    "flow_rate":          60.0,
    "ph":                 0.4,
    "energy_consumption": 50.0,
}

# Trend window: number of hours of history for linear regression
TREND_WINDOW = 6

# Trend alert: minutes-to-breach threshold
TREND_MINUTES_WARN = 120
TREND_MINUTES_CRIT = 60
