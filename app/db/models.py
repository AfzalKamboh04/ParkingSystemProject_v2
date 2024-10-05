from sqlalchemy import Column, Integer, Boolean, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base


class ParkingSlot(Base):
    __tablename__ = "parking_slots"

    id = Column(Integer, primary_key=True, index=True)
    is_occupied = Column(Boolean, default=False)


class VehicleRegistration(Base):
    __tablename__ = "vehicle_registration"

    vehicle_id = Column(Integer, primary_key=True, index=True)
    license_plate = Column(String(20), unique=True, index=True)

    parking_sessions = relationship("ParkingSession", back_populates="vehicle")


class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    session_id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(Integer, ForeignKey('parking_slots.id'))
    vehicle_id = Column(Integer, ForeignKey('vehicle_registration.vehicle_id'))
    
    check_in_time = Column(DateTime)
    check_out_time = Column(DateTime, nullable=True)
    total_parked_hours = Column(Numeric, nullable=True)
    total_rent = Column(Numeric, nullable=True)

    vehicle = relationship("VehicleRegistration", back_populates="parking_sessions")
    slot = relationship("ParkingSlot")
