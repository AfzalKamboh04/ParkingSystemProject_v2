from fastapi import FastAPI
from redis import Redis
from app.db.database import engine
from app.db.models import Base
from app.api.routes.parking import router as parking_router

# Initialize the app
app = FastAPI()

# Create Redis client
redis_client = Redis(host='localhost', port=6379, db=0)

# Create database tables if not already present
Base.metadata.create_all(bind=engine)

# Include the routes
app.include_router(parking_router)
