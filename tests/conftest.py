import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, get_db


TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=test_engine)
    
    from main import app
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def sample_mission_data():
    return {
        "name": "Test Mission",
        "flight_duration": 120.0,
        "exposure_count": 5,
        "light_sequence": ["#FF0000", "#00FF00", "#0000FF"],
        "waypoints": [
            {"order": 1, "lat": 37.7749, "lon": -122.4194, "alt": 50.0},
            {"order": 2, "lat": 37.7750, "lon": -122.4190, "alt": 55.0},
            {"order": 3, "lat": 37.7752, "lon": -122.4185, "alt": 50.0},
        ],
    }


@pytest.fixture
def created_mission(client, sample_mission_data):
    response = client.post("/missions", json=sample_mission_data)
    return response.json()
