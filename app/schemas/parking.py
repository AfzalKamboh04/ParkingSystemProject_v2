from pydantic import BaseModel
from typing import Optional,List 
from datetime import datetime

class SlotDetailsResponse(BaseModel):
    available_slots: List[int]  # Example structure

class InitializationResponse(BaseModel):
    message: str
    total_slots: int

class ParkingSlotBase(BaseModel):
    """Shared attributes for ParkingSlot."""
    id: int
    is_occupied: bool

    class Config:
        orm_mode = True


class VehicleRegistrationBase(BaseModel):
    """Shared attributes for VehicleRegistration."""
    vehicle_id: int
    license_plate: str

    class Config:
        orm_mode = True


class VehicleRegistrationCreate(BaseModel):
    """Schema for creating a new VehicleRegistration."""
    license_plate: str


class VehicleRegistrationUpdate(BaseModel):
    """Schema for updating an existing VehicleRegistration."""
    license_plate: Optional[str]


class ParkingSessionBase(BaseModel):
    """Shared attributes for ParkingSession."""
    session_id: int
    slot_id: int
    vehicle_id: int
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    total_parked_hours: Optional[float] = None
    total_rent: Optional[float] = None

    class Config:
        orm_mode = True


class ParkingSessionCreate(BaseModel):
    """Schema for creating a new ParkingSession."""
    slot_id: int
    vehicle_id: int
    check_in_time: datetime


class ParkingSessionUpdate(BaseModel):
    """Schema for updating an existing ParkingSession."""
    vehicle_id: str


class VehicleExitResponse(BaseModel):
    """Response schema for vehicle exit."""
    check_out_vehicle_no: str
    in_time: datetime
    out_time: datetime
    total_parked_hours: int
    total_rent: float


class SlotAvailabilityResponse(BaseModel):
    """Response schema for slot availability."""
    total_slots: int
    total_available_slots: int
    total_vehicle_queued: int
