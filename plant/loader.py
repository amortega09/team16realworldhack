import csv
import os
from collections import defaultdict
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'Base Dataset')


def load_hierarchy():
    """Returns {zone_name: {display_name, geometry_id}}"""
    zones = {}
    with open(os.path.join(DATA_DIR, 'plant_hierarchy.csv')) as f:
        for row in csv.DictReader(f):
            if row['hierarchy_type'] == 'zone':
                zones[row['name']] = {
                    'display_name': row['display_name'],
                    'geometry_id':  int(row['geometry_id']),
                }
    return zones


def load_metrics():
    """Returns (readings, start_dt) where readings is:
       {hour_index: {geometry_id: {metric: {agg: value}, '_working': bool}}}
    """
    readings = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    hour_meta = {}  # hour_index -> {is_working}
    start_dt = None

    with open(os.path.join(DATA_DIR, 'plant_metrics.csv')) as f:
        for row in csv.DictReader(f):
            dt = datetime.strptime(row['start_time'][:19], '%Y-%m-%d %H:%M:%S')
            if start_dt is None:
                start_dt = dt.replace(hour=0, minute=0, second=0)

            hour_idx = int((dt - start_dt).total_seconds() / 3600)
            geom_id  = int(row['geometry_id'])
            metric   = row['metric_name']
            agg      = row['aggregation']

            readings[hour_idx][geom_id][metric][agg] = float(row['value'])
            hour_meta[hour_idx] = row['is_working'].strip().lower() == 'true'

    return dict(readings), hour_meta, start_dt
