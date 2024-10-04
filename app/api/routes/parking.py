from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from redis import Redis
from app.schemas.parking import ParkingSlotBase
from app.db.models import ParkingSlot
from app.db.database import get_db
from app.services.parking_service import process_queued_vehicles, calculate_rent, initialize_slots, vehicle_registration
import json

router = APIRouter()

redis_client = Redis(host='localhost', port=6379, db=0)

@router.post("/exit_vehicle/{slot_id}")
def exit_vehicle(slot_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return process_queued_vehicles(slot_id, background_tasks, db)

@router.get("/slots_details/")
def slots_availability_details(db: Session = Depends(get_db)):
    available_slots = db.query(ParkingSlot).filter(
        (ParkingSlot.is_occupied == False) | (ParkingSlot.is_occupied.is_(None))
    ).all()

    queued_vehicle_count = redis_client.llen('vehicle_queue')
    total_slots_count = db.query(ParkingSlot.id).count()

    return {
        "total_slots": total_slots_count,
        "total_available_slots": len(available_slots),
        "total_vehicle_queued": queued_vehicle_count
    }

@router.post("/initialize_slot/{total_slots}")
def initialize_slot(total_slots: int, db: Session = Depends(get_db)):
    return initialize_slots(total_slots, db)

@router.post("/register/")
def register_vehicle(parkingslot: ParkingSlotBase, db: Session = Depends(get_db)):
    return vehicle_registration(parkingslot, db)


