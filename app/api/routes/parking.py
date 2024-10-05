from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.schemas.parking import VehicleRegistrationCreate, ParkingSessionUpdate
from app.db.database import get_db
from app.services.parking_service import (
    process_queued_vehicles, 
    calculate_rent, 
    initialize_slots, 
    vehicle_registration, 
    slot_availability_check
)

router = APIRouter()

@router.post("/exit_vehicle/")
async def exit_vehicle(checking_out: ParkingSessionUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return process_queued_vehicles(checking_out, background_tasks, db)

@router.get("/slots_details/")
async def slots_availability_details(db: Session = Depends(get_db)):
    return slot_availability_check(db)

@router.post("/initialize_slot/{total_slots}")
async def initialize_slot(total_slots: int, db: Session = Depends(get_db)):
    return initialize_slots(total_slots, db)

@router.post("/register/")
async def register_vehicle(registration: VehicleRegistrationCreate, db: Session = Depends(get_db)):
    return vehicle_registration(registration, db)
