import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Any, Dict

from config import get_settings
from middleware import RequestLoggingMiddleware, logger
from models import Base, engine, get_db, Mission, Waypoint
from schemas import MissionIn, MissionOut, MissionUpdate, WaypointIn, WaypointOut
from sync_engine import calculate_triggers, estimate_flight_time
from validators import validate_mission

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="Manage drone light-painting missions: waypoints, LED sequences, and camera sync.",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.app_name}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": getattr(request.state, "request_id", None)}
    )


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, str]:
    return {"status": "healthy", "version": settings.app_version}


@app.get("/ready", tags=["Health"])
def readiness_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        raise HTTPException(status_code=503, detail="Database not ready")


def get_mission_or_404(mission_id: int, db: Session) -> Mission:
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@app.post("/missions", response_model=MissionOut, status_code=status.HTTP_201_CREATED, tags=["Missions"])
def create_mission(payload: MissionIn, db: Session = Depends(get_db)):
    logger.info(f"Creating mission: {payload.name}")
    mission = Mission(
        name=payload.name,
        flight_duration=payload.flight_duration,
        exposure_count=payload.exposure_count,
        light_sequence=payload.light_sequence,
    )
    db.add(mission)
    db.flush()

    for wp in payload.waypoints:
        db.add(Waypoint(mission_id=mission.id, **wp.model_dump()))

    db.commit()
    db.refresh(mission)
    logger.info(f"Created mission {mission.id}: {mission.name}")
    return mission


@app.get("/missions", response_model=List[MissionOut], tags=["Missions"])
def list_missions(db: Session = Depends(get_db)):
    return db.query(Mission).all()


@app.get("/missions/{mission_id}", response_model=MissionOut, tags=["Missions"])
def get_mission(mission_id: int, db: Session = Depends(get_db)):
    return get_mission_or_404(mission_id, db)


@app.patch("/missions/{mission_id}", response_model=MissionOut, tags=["Missions"])
def update_mission(mission_id: int, payload: MissionUpdate, db: Session = Depends(get_db)):
    mission = get_mission_or_404(mission_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(mission, field, value)
    db.commit()
    db.refresh(mission)
    logger.info(f"Updated mission {mission_id}")
    return mission


@app.delete("/missions/{mission_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Missions"])
def delete_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = get_mission_or_404(mission_id, db)
    db.delete(mission)
    db.commit()
    logger.info(f"Deleted mission {mission_id}")


@app.post("/missions/{mission_id}/waypoints", response_model=WaypointOut, status_code=201, tags=["Waypoints"])
def add_waypoint(mission_id: int, payload: WaypointIn, db: Session = Depends(get_db)):
    get_mission_or_404(mission_id, db)
    wp = Waypoint(mission_id=mission_id, **payload.model_dump())
    db.add(wp)
    db.commit()
    db.refresh(wp)
    logger.info(f"Added waypoint {wp.id} to mission {mission_id}")
    return wp


@app.get("/missions/{mission_id}/waypoints", response_model=List[WaypointOut], tags=["Waypoints"])
def list_waypoints(mission_id: int, db: Session = Depends(get_db)):
    get_mission_or_404(mission_id, db)
    return db.query(Waypoint).filter(Waypoint.mission_id == mission_id).order_by(Waypoint.order).all()


@app.delete("/missions/{mission_id}/waypoints/{waypoint_id}", status_code=204, tags=["Waypoints"])
def delete_waypoint(mission_id: int, waypoint_id: int, db: Session = Depends(get_db)):
    wp = db.query(Waypoint).filter(Waypoint.id == waypoint_id, Waypoint.mission_id == mission_id).first()
    if not wp:
        raise HTTPException(status_code=404, detail="Waypoint not found")
    db.delete(wp)
    db.commit()
    logger.info(f"Deleted waypoint {waypoint_id} from mission {mission_id}")


@app.get("/missions/{mission_id}/sync", tags=["Sync"])
def get_sync_schedule(mission_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    mission = get_mission_or_404(mission_id, db)
    triggers = calculate_triggers(mission.flight_duration, mission.exposure_count, mission.light_sequence)
    return {
        "mission_id": mission.id,
        "flight_duration_s": mission.flight_duration,
        "exposure_count": mission.exposure_count,
        "triggers": triggers,
    }


@app.get("/missions/{mission_id}/validate", tags=["Validation"])
def validate(mission_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    mission = get_mission_or_404(mission_id, db)
    warnings = validate_mission(mission, waypoints_orm=mission.waypoints)
    return {
        "mission_id": mission.id,
        "safe": len(warnings) == 0,
        "warnings": warnings,
    }


@app.get("/missions/{mission_id}/export", tags=["Export"])
def export_mission(mission_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    mission = get_mission_or_404(mission_id, db)
    sorted_wps = sorted(mission.waypoints, key=lambda w: w.order)
    triggers = calculate_triggers(mission.flight_duration, mission.exposure_count, mission.light_sequence)

    return {
        "format_version": "1.0",
        "mission": {
            "id": mission.id,
            "name": mission.name,
            "flight_duration_s": mission.flight_duration,
        },
        "waypoints": [
            {"order": w.order, "lat": w.lat, "lon": w.lon, "alt_m": w.alt}
            for w in sorted_wps
        ],
        "camera_sync": triggers,
        "light_sequence": mission.light_sequence,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
