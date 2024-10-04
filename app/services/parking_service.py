import json
import math
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from redis import Redis
from app.db.models import ParkingSlot
from app.schemas.parking import ParkingSlotBase
from app.utils.datetime_encoder import DateTimeEncoder


redis_client = Redis(host='localhost', port=6379, db=0)

def process_queued_vehicles(slot_id: int, background_tasks, db: Session):
    parking_slot = db.query(ParkingSlot).filter(ParkingSlot.id == slot_id).first()
    if not parking_slot:
        raise HTTPException(status_code=404, detail="Parking slot not found.")
    if parking_slot.is_occupied is False:
        raise HTTPException(status_code=400, detail="The parking slot is already vacant.")

    entering_time = parking_slot.entering_time
    exit_time = datetime.now()
    time_difference = exit_time - entering_time
    hours_difference = time_difference.total_seconds() / 3600
    rounded_hours = math.ceil(hours_difference) if hours_difference > 0 else 0

    total_rent = rounded_hours * 50

    parking_slot.is_occupied = False
    parking_slot.vehicle_number = None
    parking_slot.entering_time = None
    db.commit()

    background_tasks.add_task(assign_queued_vehicle, db)
    
    return {
        "free_slot_id": slot_id,
        "check_out_vehicle_no": parking_slot.vehicle_number,
        "in_time": entering_time,
        "out_time": exit_time,
        "total_parked_hours": rounded_hours,
        "total_rent": total_rent
    }

def assign_queued_vehicle(db: Session):
    queued_vehicle_data = redis_client.lpop("vehicle_queue")
    if queued_vehicle_data:
        vehicle = json.loads(queued_vehicle_data)
        available_slot = db.query(ParkingSlot).filter(ParkingSlot.is_occupied == False).first()
        if available_slot:
            available_slot.vehicle_number = vehicle['vehicle_number']
            available_slot.entering_time = vehicle.get("entering_time", datetime.now())
            available_slot.is_occupied = True
            db.commit()

def initialize_slots(total_slots: int, db: Session):
    for _ in range(total_slots):
        new_slot = ParkingSlot(is_occupied=False, vehicle_number=None, entering_time=None)
        db.add(new_slot)
    db.commit()

    return {"message": "Slots initialized successfully", "total_slots": total_slots}

def calculate_rent(entering_time: datetime, exit_time: datetime) -> float:
    """Calculates parking rent based on hourly rate."""
    time_difference = exit_time - entering_time
    hours_difference = time_difference.total_seconds() / 3600
    rounded_hours = math.ceil(hours_difference) if hours_difference > 0 else 0
    rate_per_hour = 50
    total_rent = rounded_hours * rate_per_hour
    return total_rent

def vehicle_registration(parkingslot:ParkingSlotBase, db:Session):
    """Register a vehicle to a parking slot or queue it if no slots are available."""
    
    # Count total parking slots in the database
    total_slots_db = db.query(ParkingSlot.id).count()

    # Check if the vehicle is already occupying a slot
    user_occupied_slots = db.query(ParkingSlot).filter(
        ParkingSlot.vehicle_number == parkingslot.vehicle_number, 
        ParkingSlot.is_occupied == True
    ).count()

    # If the user has not exceeded their slot limit
    if user_occupied_slots < total_slots_db:
        available_slots = db.query(ParkingSlot).filter(
            (ParkingSlot.is_occupied == False) | (ParkingSlot.is_occupied.is_(None))
        ).all()

        # No available slots, queue the vehicle in Redis
        if not available_slots:
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print(parkingslot.dict())
            redis_data = json.dumps(parkingslot.dict(), cls=DateTimeEncoder)
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print(redis_data)
            redis_client.rpush('vehicle_queue', redis_data)
            return {"message": "No available slots. Your request has been queued."}

        # If there's an available slot, assign the vehicle
        slot_to_update = available_slots[0]
        slot_to_update.vehicle_number = parkingslot.vehicle_number
        slot_to_update.entering_time = parkingslot.entering_time
        slot_to_update.is_occupied = True

        db.commit()

        remaining_slots = len(available_slots) - 1

        return {
            "assigned_slot": slot_to_update.id,
            "vehicle_plate_number": slot_to_update.vehicle_number,
            "entrance_time": slot_to_update.entering_time,
            "available_slots": remaining_slots
        }
    else:
        raise HTTPException(status_code=403, detail="You exceeded your slot limit.")
