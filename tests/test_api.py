"""
API integration tests
Run with: pytest tests/test_api.py -v
"""
import pytest


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_readiness_check(client):
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_create_mission(client, sample_mission_data):
    response = client.post("/missions", json=sample_mission_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_mission_data["name"]
    assert data["flight_duration"] == sample_mission_data["flight_duration"]
    assert len(data["waypoints"]) == 3


def test_create_mission_invalid_lat(client):
    data = {
        "name": "Test",
        "flight_duration": 120,
        "exposure_count": 5,
        "light_sequence": ["#FF0000"],
        "waypoints": [
            {"order": 1, "lat": 100, "lon": 0, "alt": 50},
            {"order": 2, "lat": 0, "lon": 0, "alt": 50},
        ],
    }
    response = client.post("/missions", json=data)
    assert response.status_code == 422


def test_create_mission_empty_light_sequence(client):
    data = {
        "name": "Test",
        "flight_duration": 120,
        "exposure_count": 5,
        "light_sequence": [],
        "waypoints": [
            {"order": 1, "lat": 37.77, "lon": -122.41, "alt": 50},
            {"order": 2, "lat": 37.78, "lon": -122.40, "alt": 55},
        ],
    }
    response = client.post("/missions", json=data)
    assert response.status_code == 201


def test_list_missions(client, created_mission):
    response = client.get("/missions")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_mission(client, created_mission):
    mission_id = created_mission["id"]
    response = client.get(f"/missions/{mission_id}")
    assert response.status_code == 200
    assert response.json()["id"] == mission_id


def test_get_mission_not_found(client):
    response = client.get("/missions/99999")
    assert response.status_code == 404


def test_update_mission(client, created_mission):
    mission_id = created_mission["id"]
    response = client.patch(f"/missions/{mission_id}", json={"name": "Updated Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_delete_mission(client, created_mission):
    mission_id = created_mission["id"]
    response = client.delete(f"/missions/{mission_id}")
    assert response.status_code == 204
    response = client.get(f"/missions/{mission_id}")
    assert response.status_code == 404


def test_add_waypoint(client, created_mission):
    mission_id = created_mission["id"]
    new_wp = {"order": 4, "lat": 37.7755, "lon": -122.4180, "alt": 60.0}
    response = client.post(f"/missions/{mission_id}/waypoints", json=new_wp)
    assert response.status_code == 201
    assert response.json()["order"] == 4


def test_list_waypoints(client, created_mission):
    mission_id = created_mission["id"]
    response = client.get(f"/missions/{mission_id}/waypoints")
    assert response.status_code == 200
    waypoints = response.json()
    assert len(waypoints) == 3
    orders = [wp["order"] for wp in waypoints]
    assert orders == sorted(orders)


def test_delete_waypoint(client, created_mission):
    mission_id = created_mission["id"]
    waypoints = client.get(f"/missions/{mission_id}/waypoints").json()
    wp_id = waypoints[0]["id"]
    response = client.delete(f"/missions/{mission_id}/waypoints/{wp_id}")
    assert response.status_code == 204


def test_get_sync_schedule(client, created_mission):
    mission_id = created_mission["id"]
    response = client.get(f"/missions/{mission_id}/sync")
    assert response.status_code == 200
    data = response.json()
    assert "triggers" in data
    assert len(data["triggers"]) == 5


def test_get_sync_schedule_empty_light(client, sample_mission_data):
    sample_mission_data["light_sequence"] = []
    response = client.post("/missions", json=sample_mission_data)
    mission_id = response.json()["id"]
    response = client.get(f"/missions/{mission_id}/sync")
    assert response.status_code == 200
    data = response.json()
    assert all(t["light_color"] is None for t in data["triggers"])


def test_validate_mission(client, created_mission):
    mission_id = created_mission["id"]
    response = client.get(f"/missions/{mission_id}/validate")
    assert response.status_code == 200
    data = response.json()
    assert "safe" in data
    assert "warnings" in data


def test_export_mission(client, created_mission):
    mission_id = created_mission["id"]
    response = client.get(f"/missions/{mission_id}/export")
    assert response.status_code == 200
    data = response.json()
    assert "format_version" in data
    assert "mission" in data
    assert "waypoints" in data
    assert "camera_sync" in data
    assert "light_sequence" in data
    waypoints = data["waypoints"]
    orders = [w["order"] for w in waypoints]
    assert orders == sorted(orders)
