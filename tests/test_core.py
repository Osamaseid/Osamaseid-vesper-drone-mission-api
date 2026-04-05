"""
Unit tests for Vesper sync engine and validators.
Run with: pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sync_engine import calculate_triggers, estimate_flight_time
from validators import validate_mission


class FakeWaypoint:
    def __init__(self, lat, lon, alt):
        self.lat, self.lon, self.alt = lat, lon, alt


class FakeMission:
    def __init__(self, flight_duration, exposure_count, light_sequence, waypoints=None):
        self.flight_duration = flight_duration
        self.exposure_count = exposure_count
        self.light_sequence = light_sequence
        self.waypoints = waypoints or []


def test_triggers_single_exposure():
    """Single exposure → one trigger at t=0."""
    result = calculate_triggers(120, 1, ["#FF0000"])
    assert len(result) == 1
    assert result[0]["timestamp_ms"] == 0
    assert result[0]["light_color"] == "#FF0000"


def test_triggers_five_exposures_even_spacing():
    """5 exposures over 120s → timestamps at 0, 30000, 60000, 90000, 120000 ms."""
    result = calculate_triggers(120, 5, ["#FF0000", "#00FF00", "#0000FF", "#FFFFFF", "#000000"])
    timestamps = [t["timestamp_ms"] for t in result]
    assert timestamps == [0, 30000, 60000, 90000, 120000]


def test_triggers_color_cycling():
    """Colors cycle when exposure_count > len(light_sequence)."""
    result = calculate_triggers(60, 4, ["#AAAAAA", "#BBBBBB"])
    colors = [t["light_color"] for t in result]
    assert colors == ["#AAAAAA", "#BBBBBB", "#AAAAAA", "#BBBBBB"]


def test_triggers_three_exposures_60s():
    """3 exposures over 60s → 0, 30000, 60000 ms."""
    result = calculate_triggers(60, 3, ["#FF0000"])
    assert [t["timestamp_ms"] for t in result] == [0, 30000, 60000]


def test_triggers_ten_exposures_100s():
    """10 exposures over 100s → interval of ~11111ms."""
    result = calculate_triggers(100, 10, ["#123456"])
    assert len(result) == 10
    assert result[0]["timestamp_ms"] == 0
    assert result[-1]["timestamp_ms"] == 100000


def test_triggers_trigger_index_sequential():
    """trigger_index must be 1-based and sequential."""
    result = calculate_triggers(90, 3, ["#FF0000"])
    assert [t["trigger_index"] for t in result] == [1, 2, 3]


def test_triggers_empty_light_sequence():
    """Empty light sequence should not crash and return None colors."""
    result = calculate_triggers(120, 5, [])
    assert len(result) == 5
    assert all(t["light_color"] is None for t in result)


def test_estimate_flight_time_basic():
    """Two waypoints ~111m apart at 5m/s → ~22s."""
    wps = [FakeWaypoint(0.0, 0.0, 0), FakeWaypoint(0.001, 0.0, 0)]
    t = estimate_flight_time(wps, speed_ms=5.0)
    assert 20 < t < 25


def test_estimate_flight_time_altitude_delta():
    """Altitude difference contributes to 3D distance."""
    wps = [FakeWaypoint(0.0, 0.0, 0), FakeWaypoint(0.0, 0.0, 100)]
    t = estimate_flight_time(wps, speed_ms=5.0)
    assert abs(t - 20.0) < 0.1


def test_estimate_flight_time_empty_waypoints():
    """Empty waypoints should return 0."""
    t = estimate_flight_time([], speed_ms=5.0)
    assert t == 0.0


def test_estimate_flight_time_single_waypoint():
    """Single waypoint should return 0."""
    wps = [FakeWaypoint(0.0, 0.0, 50)]
    t = estimate_flight_time(wps, speed_ms=5.0)
    assert t == 0.0


def test_validate_safe_mission():
    """A well-configured mission should produce no warnings."""
    wps = [FakeWaypoint(0.0, 0.0, 50), FakeWaypoint(0.001, 0.0, 50)]
    mission = FakeMission(flight_duration=300, exposure_count=5,
                          light_sequence=["#FF0000", "#00FF00"], waypoints=wps)
    assert validate_mission(mission, waypoints_orm=wps) == []


def test_validate_flight_too_short():
    """Mission flagged when flight_duration is too short for the waypoint path."""
    wps = [FakeWaypoint(0.0, 0.0, 0), FakeWaypoint(1.0, 0.0, 0)]
    mission = FakeMission(flight_duration=10, exposure_count=3,
                          light_sequence=["#FF0000"], waypoints=wps)
    warnings = validate_mission(mission, waypoints_orm=wps)
    assert any("too short" in w for w in warnings)


def test_validate_light_sequence_exceeds_exposures():
    """Warning when light sequence has more colors than exposures."""
    wps = [FakeWaypoint(0.0, 0.0, 50), FakeWaypoint(0.001, 0.0, 50)]
    mission = FakeMission(flight_duration=300, exposure_count=2,
                          light_sequence=["#FF0000", "#00FF00", "#0000FF"], waypoints=wps)
    warnings = validate_mission(mission, waypoints_orm=wps)
    assert any("more colors than exposures" in w for w in warnings)
