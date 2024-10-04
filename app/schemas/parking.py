from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ParkingSlotBase(BaseModel):
    vehicle_number: str
    entering_time: Optional[datetime] = datetime.now()

    class Config:
        from_attributes = True  # Update from Pydantic v2

