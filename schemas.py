import re
from pydantic import BaseModel, field_validator
from typing import List, Optional
from config import get_settings

settings = get_settings()

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class WaypointIn(BaseModel):
    order: int
    lat: float
    lon: float
    alt: float

    @field_validator("order")
    @classmethod
    def order_positive(cls, v):
        if v < 1:
            raise ValueError("Waypoint order must be at least 1")
        return v

    @field_validator("lat")
    @classmethod
    def lat_valid(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("lon")
    @classmethod
    def lon_valid(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v

    @field_validator("alt")
    @classmethod
    def alt_positive(cls, v):
        if v < 0:
            raise ValueError("Altitude must be non-negative")
        return v


class WaypointOut(WaypointIn):
    id: int
    mission_id: int

    model_config = {"from_attributes": True}


class MissionIn(BaseModel):
    name: str
    flight_duration: float
    exposure_count: int
    light_sequence: List[str]
    waypoints: List[WaypointIn]

    @field_validator("flight_duration")
    @classmethod
    def duration_positive(cls, v):
        if v <= 0:
            raise ValueError("flight_duration must be positive")
        return v

    @field_validator("exposure_count")
    @classmethod
    def exposures_positive_and_reasonable(cls, v):
        if v < 1:
            raise ValueError("exposure_count must be at least 1")
        if v > settings.max_exposure_count:
            raise ValueError(f"exposure_count cannot exceed {settings.max_exposure_count}")
        return v

    @field_validator("light_sequence")
    @classmethod
    def valid_hex(cls, v):
        for color in v:
            if not HEX_RE.match(color):
                raise ValueError(f"Invalid HEX color: {color}. Expected format #RRGGBB")
        return v

    @field_validator("waypoints")
    @classmethod
    def min_waypoints(cls, v):
        if len(v) < 2:
            raise ValueError("A mission requires at least 2 waypoints")
        return v


class MissionOut(BaseModel):
    id: int
    name: str
    flight_duration: float
    exposure_count: int
    light_sequence: List[str]
    waypoints: List[WaypointOut]

    model_config = {"from_attributes": True}


class MissionUpdate(BaseModel):
    name: Optional[str] = None
    flight_duration: Optional[float] = None
    exposure_count: Optional[int] = None
    light_sequence: Optional[List[str]] = None

    @field_validator("flight_duration")
    @classmethod
    def duration_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("flight_duration must be positive")
        return v

    @field_validator("exposure_count")
    @classmethod
    def exposures_positive_and_reasonable(cls, v):
        if v is not None:
            if v < 1:
                raise ValueError("exposure_count must be at least 1")
            if v > settings.max_exposure_count:
                raise ValueError(f"exposure_count cannot exceed {settings.max_exposure_count}")
        return v

    @field_validator("light_sequence")
    @classmethod
    def valid_hex(cls, v):
        if v is not None:
            for color in v:
                if not HEX_RE.match(color):
                    raise ValueError(f"Invalid HEX color: {color}")
        return v
