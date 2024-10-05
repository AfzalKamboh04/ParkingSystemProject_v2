import json
import math
from sqlalchemy import text
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from redis import Redis
from app.schemas.parking import VehicleRegistrationCreate, ParkingSessionUpdate
from app.utils.datetime_encoder import DateTimeEncoder
from app.db.models import VehicleRegistration, ParkingSlot, ParkingSession
from app.core.config import Settings
from sqlalchemy.exc import SQLAlchemyError

# Redis client initialization
redis_client = Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT, db=0)

def process_queued_vehicles(vehicle_timeout: ParkingSessionUpdate, background_tasks, db: Session):
    try:
        vehicle_checkout = db.query(VehicleRegistration).filter(
            VehicleRegistration.license_plate == vehicle_timeout.vehicle_id
        ).first()

        if vehicle_checkout is None:
            raise HTTPException(status_code=400, detail="Vehicle Registration Not Found")

        parking_session = db.query(ParkingSession).filter(
            ParkingSession.vehicle_id == vehicle_checkout.vehicle_id,
            ParkingSession.check_out_time == None
        ).first()

        if parking_session is None:
            raise HTTPException(status_code=400, detail="No active parking session found for the vehicle")

        slot_number = db.query(ParkingSlot).filter(ParkingSlot.id == parking_session.slot_id).first()
        check_out_time = datetime.now()
        
        # Calculate total rent
        total_rent = calculate_rent(parking_session.check_in_time, check_out_time)
        parking_session.check_out_time = check_out_time
        parking_session.total_parked_hours = total_rent["rounded_hours"]
        parking_session.total_rent = total_rent["rent"]
        slot_number.is_occupied = False
        db.commit()
        
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error Processing Vehicle: {e}")

    # Assign the next queued vehicle in the background
    background_tasks.add_task(assign_queued_vehicle, db)

    return {
        "check_out_vehicle_no": parking_session.vehicle_id,
        "in_time": parking_session.check_in_time,
        "out_time": check_out_time,
        "total_parked_hours": total_rent["rounded_hours"],
        "total_rent": total_rent["rent"]
    }

def assign_queued_vehicle(db: Session):
    try:
        # Pop vehicle data from Redis queue
        queued_vehicle_data = redis_client.lpop("vehicle_queue")
        
        if not queued_vehicle_data:
            raise HTTPException(status_code=400, detail="No queued vehicle found")

        vehicle = json.loads(queued_vehicle_data)
        if 'vehicle_number' not in vehicle or 'entering_time' not in vehicle:
            raise HTTPException(status_code=400, detail="Required vehicle data is missing")

        # Find the first available parking slot
        available_slot = db.query(ParkingSlot).filter(ParkingSlot.is_occupied == False).first()
        
        if available_slot:
            vehicle_session = ParkingSession(
                vehicle_id=vehicle['vehicle_number'],
                slot_id=available_slot.id,
                check_in_time=vehicle.get("entering_time", datetime.now())
            )
            
            db.add(vehicle_session)
            available_slot.is_occupied = True
            db.commit()
            db.refresh(vehicle_session)
            db.refresh(available_slot)
        else:
            raise HTTPException(status_code=400, detail="No available parking slot found")

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

def calculate_rent(entering_time: datetime, exit_time: datetime) -> dict:
    """Calculates parking rent based on hourly rate."""
    time_difference = exit_time - entering_time
    hours_difference = time_difference.total_seconds() / 3600
    rounded_hours = math.ceil(hours_difference) if hours_difference > 0 else 0
    rate_per_hour = 50
    total_rent = rounded_hours * rate_per_hour
    return {
        "rounded_hours": rounded_hours,
        "rent": total_rent
    }

def slot_availability_check(db: Session):
    # Count the available slots directly
    available_slots_count = db.query(ParkingSlot).filter(
        (ParkingSlot.is_occupied == False)
    ).count()

    queued_vehicle_count = redis_client.llen('vehicle_queue')
    total_slots_count = db.query(ParkingSlot.id).count()

    return {
        "total_slots": total_slots_count,
        "total_available_slots": available_slots_count,
        "total_vehicle_queued": queued_vehicle_count
    }


def initialize_slots(total_slots: int, db: Session):
    if total_slots < 0:
        raise HTTPException(status_code=400, detail="Slot limit must be a non-negative integer.")
    
    slots = [ParkingSlot(is_occupied=False) for _ in range(total_slots)]
    db.bulk_save_objects(slots)
    db.commit()

    return {"message": "Total slots limit updated successfully", "total_slots": total_slots}

def parkings_sessions(vehicle_id, check_in_time, db: Session):
    # Query for an available parking slot
    available_slot = db.query(ParkingSlot).filter(ParkingSlot.is_occupied == False).first()
    
    if not available_slot:
        vehicle_queuing_details = {
            "vehicle_number": vehicle_id,
            "entering_time": check_in_time
        }
        redis_data = json.dumps(vehicle_queuing_details, cls=DateTimeEncoder)
        redis_client.rpush('vehicle_queue', redis_data)
        
        return { 
            "message": "Vehicle queued successfully", 
            "vehicle_id": vehicle_id 
        }
    
    try:
        vehicle_session = ParkingSession(
            vehicle_id=vehicle_id,
            slot_id=available_slot.id,
            check_in_time=check_in_time
        )
        
        db.add(vehicle_session)
        available_slot.is_occupied = True
        db.commit()
        db.refresh(vehicle_session)
        db.refresh(available_slot)
        
        return {
            "message": "Vehicle parked successfully",
            "vehicle_id": vehicle_id,
            "slot_id": available_slot.id,
            "check_in_time": vehicle_session.check_in_time,
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

def vehicle_registration(vehicleRegistrationC: VehicleRegistrationCreate, db: Session):
    try:
        existing_vehicle = db.query(VehicleRegistration).filter_by(license_plate=vehicleRegistrationC.license_plate).first()

        if not existing_vehicle:
            vehicle_registration = VehicleRegistration(
                license_plate=vehicleRegistrationC.license_plate,
            )
            db.add(vehicle_registration)
            db.commit()
            db.refresh(vehicle_registration)

            response = parkings_sessions(vehicle_registration.vehicle_id, str(datetime.now()), db)
        else:
            response = parkings_sessions(existing_vehicle.vehicle_id, str(datetime.now()), db)
        
        return response

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Vehicle not registered: {e}")
