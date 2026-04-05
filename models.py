from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()
engine = create_engine(
    "sqlite:///./vesper.db",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Mission(Base):
    __tablename__ = "missions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    flight_duration = Column(Float, nullable=False)
    exposure_count = Column(Integer, nullable=False, index=True)
    light_sequence = Column(JSON, nullable=False)
    waypoints = relationship("Waypoint", back_populates="mission", cascade="all, delete-orphan")


class Waypoint(Base):
    __tablename__ = "waypoints"
    
    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False, index=True)
    order = Column(Integer, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    alt = Column(Float, nullable=False)
    mission = relationship("Mission", back_populates="waypoints")
