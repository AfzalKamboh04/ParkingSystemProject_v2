from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.database import Base

class ParkingSlot(Base):
    __tablename__ = "parking_slot"

    id = Column(Integer, primary_key=True, index=True)
    is_occupied = Column(Boolean, default=False)
    vehicle_number = Column(String(50), nullable=True)
    entering_time = Column(DateTime, nullable=True)
