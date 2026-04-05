"""
Sync Logic Engine — calculates camera trigger timestamps and assigns
light colors to each exposure.
"""
from typing import List, Dict, Any


def calculate_triggers(flight_duration: float, exposure_count: int, light_sequence: List[str]) -> List[Dict[str, Any]]:
    """
    Distribute `exposure_count` triggers evenly across `flight_duration` seconds.
    Returns a list of trigger events with millisecond timestamps and assigned colors.

    Interval formula:
        If exposure_count == 1  → single trigger at t=0
        Otherwise               → interval = flight_duration / (exposure_count - 1)
                                  triggers at 0, interval, 2*interval, …, flight_duration
    """
    if exposure_count == 1:
        timestamps_ms = [0]
    else:
        interval = flight_duration / (exposure_count - 1)
        timestamps_ms = [round(i * interval * 1000) for i in range(exposure_count)]

    triggers = []
    seq_len = len(light_sequence) if light_sequence else 1
    for idx, ts in enumerate(timestamps_ms):
        color = light_sequence[idx % seq_len] if light_sequence else None
        triggers.append({
            "trigger_index": idx + 1,
            "timestamp_ms": ts,
            "light_color": color,
        })
    return triggers


def estimate_flight_time(waypoints: list, speed_ms: float = 5.0) -> float:
    """
    Estimate total flight time (seconds) given ordered waypoints and a constant speed.
    Uses the Haversine formula for lat/lon distance + Euclidean for altitude delta.
    """
    from math import radians, sin, cos, sqrt, atan2

    def haversine(wp1, wp2) -> float:
        R = 6_371_000  # Earth radius in metres
        lat1, lon1 = radians(wp1.lat), radians(wp1.lon)
        lat2, lon2 = radians(wp2.lat), radians(wp2.lon)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        horizontal = 2 * R * atan2(sqrt(a), sqrt(1 - a))
        vertical = abs(wp2.alt - wp1.alt)
        return sqrt(horizontal ** 2 + vertical ** 2)

    total_dist = sum(haversine(waypoints[i], waypoints[i + 1]) for i in range(len(waypoints) - 1))
    return total_dist / speed_ms if speed_ms > 0 else 0.0
