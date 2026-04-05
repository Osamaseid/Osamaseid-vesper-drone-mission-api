# Vesper Drone Light-Painting Mission API

A production-ready REST API built with **FastAPI** for managing drone light-painting missions. It coordinates flight waypoints, programmable LED color sequences, and camera shutter sync schedules — enabling precise, repeatable aerial light-painting photography.

---

## What It Does

Drone light-painting is a photography technique where a drone equipped with programmable LEDs flies a pre-planned path while a camera captures long-exposure shots. This API handles:

- **Mission planning** — define flight duration, waypoints, and LED color sequences
- **Camera sync scheduling** — automatically calculate when the camera shutter should trigger during the flight
- **Safety validation** — check if the planned flight duration is realistic for the waypoint path
- **Flight controller export** — generate a structured payload ready to upload to a drone flight controller

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 |
| Database | SQLite via SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Server | Uvicorn |
| Testing | Pytest + HTTPX |
| Config | pydantic-settings + python-dotenv |

---

## Project Structure

```
vesper-api/
├── main.py           # FastAPI app, all route handlers, middleware setup
├── models.py         # SQLAlchemy ORM models (Mission, Waypoint) + DB engine
├── schemas.py        # Pydantic request/response schemas with input validation
├── sync_engine.py    # Camera trigger timestamp calculations + Haversine distance
├── validators.py     # Safety validation logic (flight time, light sequence checks)
├── config.py         # App settings via pydantic-settings (.env support)
├── middleware.py     # Request logging middleware with unique request IDs
├── requirements.txt  # Python dependencies
├── docker-compose.yml
└── tests/
    └── test_core.py  # Unit tests for sync engine and validators
```

---

## Setup & Run Locally

### 1. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment (optional)

Create a `.env` file in the project root to override defaults:

```env
DEBUG=true
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./vesper.db
HOST=0.0.0.0
PORT=8080
```

> Setting `DEBUG=true` enables Swagger UI and ReDoc documentation endpoints.

### 4. Start the API server

```bash
uvicorn main:app --reload --port 8080
```

The API will be available at `http://127.0.0.1:8080`.

### 5. Interactive API Docs

- Swagger UI: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
- ReDoc: [http://127.0.0.1:8080/redoc](http://127.0.0.1:8080/redoc)
- OpenAPI JSON: [http://127.0.0.1:8080/openapi.json](http://127.0.0.1:8080/openapi.json)

---

## Run with Docker

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8080`.

---

## Running Tests

```bash
pytest tests/ -v
```

Tests cover:
- Single and multi-exposure trigger calculations
- Color cycling when exposure count exceeds sequence length
- Haversine-based flight time estimation (2D and 3D)
- Safety validation warnings (short flight duration, excess colors)

---

## API Endpoints

### Health

| Method | Endpoint  | Description               |
|--------|-----------|---------------------------|
| `GET`  | `/health` | Returns API health status |
| `GET`  | `/ready`  | Checks database connection |

### Missions

| Method   | Endpoint          | Description                     |
|----------|-------------------|---------------------------------|
| `POST`   | `/missions`       | Create a mission with waypoints |
| `GET`    | `/missions`       | List all missions               |
| `GET`    | `/missions/{id}`  | Get a mission by ID             |
| `PATCH`  | `/missions/{id}`  | Update mission metadata         |
| `DELETE` | `/missions/{id}`  | Delete a mission                |

### Waypoints

| Method   | Endpoint                           | Description          |
|----------|------------------------------------|----------------------|
| `POST`   | `/missions/{id}/waypoints`         | Add a waypoint       |
| `GET`    | `/missions/{id}/waypoints`         | List all waypoints   |
| `DELETE` | `/missions/{id}/waypoints/{wp_id}` | Delete a waypoint    |

### Mission Tools

| Method | Endpoint                   | Description                      |
|--------|----------------------------|----------------------------------|
| `GET`  | `/missions/{id}/sync`      | Get camera trigger schedule      |
| `GET`  | `/missions/{id}/validate`  | Run safety validation            |
| `GET`  | `/missions/{id}/export`    | Export flight controller payload |

---

## Input Validation Rules

| Field | Rule |
|---|---|
| `flight_duration` | Must be > 0 |
| `exposure_count` | Must be ≥ 1 |
| `light_sequence` | Each color must match `#RRGGBB` hex format |
| `waypoints` | At least 2 waypoints required per mission |
| `alt` | Must be ≥ 0 (non-negative altitude) |
| `lat` | Must be between -90 and 90 |
| `lon` | Must be between -180 and 180 |
| `order` | Must be ≥ 1 |

---

## Example: Create a Mission

```bash
curl -X POST http://127.0.0.1:8080/missions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sunset Rooftop Shoot",
    "flight_duration": 120,
    "exposure_count": 5,
    "light_sequence": ["#FF0000", "#FF7700", "#FFFF00", "#00FF00", "#0000FF"],
    "waypoints": [
      {"order": 1, "lat": 37.7749, "lon": -122.4194, "alt": 50},
      {"order": 2, "lat": 37.7750, "lon": -122.4190, "alt": 55},
      {"order": 3, "lat": 37.7752, "lon": -122.4185, "alt": 50}
    ]
  }'
```

Response:

```json
{
  "id": 1,
  "name": "Sunset Rooftop Shoot",
  "flight_duration": 120.0,
  "exposure_count": 5,
  "light_sequence": ["#FF0000", "#FF7700", "#FFFF00", "#00FF00", "#0000FF"],
  "waypoints": [
    {"id": 1, "mission_id": 1, "order": 1, "lat": 37.7749, "lon": -122.4194, "alt": 50.0},
    {"id": 2, "mission_id": 1, "order": 2, "lat": 37.7750, "lon": -122.4190, "alt": 55.0},
    {"id": 3, "mission_id": 1, "order": 3, "lat": 37.7752, "lon": -122.4185, "alt": 50.0}
  ]
}
```

---

## Example: Get Camera Sync Schedule

```bash
curl http://127.0.0.1:8080/missions/1/sync
```

Response:

```json
{
  "mission_id": 1,
  "flight_duration_s": 120,
  "exposure_count": 5,
  "triggers": [
    {"trigger_index": 1, "timestamp_ms": 0, "light_color": "#FF0000"},
    {"trigger_index": 2, "timestamp_ms": 30000, "light_color": "#FF7700"},
    {"trigger_index": 3, "timestamp_ms": 60000, "light_color": "#FFFF00"},
    {"trigger_index": 4, "timestamp_ms": 90000, "light_color": "#00FF00"},
    {"trigger_index": 5, "timestamp_ms": 120000, "light_color": "#0000FF"}
  ]
}
```

---

## Example: Safety Validation

```bash
curl http://127.0.0.1:8080/missions/1/validate
```

Response when safe:

```json
{"mission_id": 1, "safe": true, "warnings": []}
```

Response with warnings:

```json
{
  "mission_id": 1,
  "safe": false,
  "warnings": [
    "Planned flight_duration (10.0s) is too short for the waypoint path at max speed 5.0m/s (estimated minimum: 22.3s)."
  ]
}
```

---

## Example: Export Flight Controller Payload

```bash
curl http://127.0.0.1:8080/missions/1/export
```

Response:

```json
{
  "format_version": "1.0",
  "mission": {"id": 1, "name": "Sunset Rooftop Shoot", "flight_duration_s": 120.0},
  "waypoints": [
    {"order": 1, "lat": 37.7749, "lon": -122.4194, "alt_m": 50.0},
    {"order": 2, "lat": 37.7750, "lon": -122.4190, "alt_m": 55.0},
    {"order": 3, "lat": 37.7752, "lon": -122.4185, "alt_m": 50.0}
  ],
  "camera_sync": [
    {"trigger_index": 1, "timestamp_ms": 0, "light_color": "#FF0000"},
    {"trigger_index": 2, "timestamp_ms": 30000, "light_color": "#FF7700"}
  ],
  "light_sequence": ["#FF0000", "#FF7700", "#FFFF00", "#00FF00", "#0000FF"]
}
```

---

## Sync Logic

Camera triggers are distributed evenly across the flight duration:

- **1 exposure** → single trigger at `t = 0ms`
- **N exposures** → `interval = flight_duration / (N - 1)`, triggers at `0, interval, 2×interval, …, flight_duration`

Light colors from `light_sequence` are assigned **cyclically** — if there are more exposures than colors, the sequence repeats from the beginning.

---

## Safety Validation Logic

The validator checks two conditions:

1. **Excess light colors** — warns if `light_sequence` has more colors than `exposure_count` (unused colors)
2. **Flight duration too short** — estimates the minimum flight time using **3D Haversine distance** across all waypoints at the maximum safe speed (5 m/s). Warns if `flight_duration` is less than 90% of the estimated minimum

---

## Error Responses

All errors follow a consistent format:

```json
{"detail": "Mission not found"}
```

| Status Code | Meaning |
|---|---|
| `400` | Validation error (invalid input) |
| `404` | Mission or waypoint not found |
| `503` | Database not ready |
| `500` | Internal server error |
