"""
Safety Validation — checks missions against operational constraints.
"""
from typing import List
from config import get_settings
from sync_engine import estimate_flight_time

settings = get_settings()


def validate_mission(mission_in, waypoints_orm=None) -> List[str]:
    """
    Returns a list of warning/error strings. Empty list means mission is safe.
    `mission_in` can be a MissionIn schema or an ORM Mission object.
    `waypoints_orm` is used when validating an existing ORM mission.
    """
    warnings = []
    waypoints = waypoints_orm or getattr(mission_in, "waypoints", [])

    light_seq = mission_in.light_sequence
    if light_seq:
        if len(light_seq) > mission_in.exposure_count:
            warnings.append(
                f"Light sequence ({len(light_seq)} colors) has more colors than exposures ({mission_in.exposure_count}). "
                f"Some colors won't be used."
            )

    if len(waypoints) >= 2:
        estimated_time = estimate_flight_time(waypoints, speed_ms=settings.max_speed_ms)
        if mission_in.flight_duration < estimated_time * 0.9:
            warnings.append(
                f"Planned flight_duration ({mission_in.flight_duration:.1f}s) is too short for the waypoint path "
                f"at max speed {settings.max_speed_ms}m/s (estimated minimum: {estimated_time:.1f}s)."
            )

    return warnings
