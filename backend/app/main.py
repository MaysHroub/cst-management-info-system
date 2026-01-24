from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import setup_indexes
from app.routers import requests, citizens, agents, analytics

app = FastAPI(
    title="Citizen Services Tracker (CST)",
    description="Advanced Municipal Service Tracking System",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    setup_indexes()

app.include_router(requests.router)
app.include_router(citizens.router)
app.include_router(agents.router)
app.include_router(analytics.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Citizen Services Tracker API"}
