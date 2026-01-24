from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.database import get_database
from app.models.schemas import Citizen, CitizenCreate, CitizenVerificationState

router = APIRouter(prefix="/citizens", tags=["Citizens"])
db = get_database()

@router.post("/")
async def create_citizen(citizen: CitizenCreate):
    # Check if email exists
    if citizen.contacts.email:
        existing = db.citizens.find_one({"contacts.email": citizen.contacts.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
            
    new_citizen = citizen.dict()
    new_citizen["verification_state"] = CitizenVerificationState.UNVERIFIED
    new_citizen["created_at"] = datetime.utcnow()
    new_citizen["stats"] = {"total_requests": 0, "avg_rating": 0}
    
    try:
        result = db.citizens.insert_one(new_citizen)
        created = db.citizens.find_one({"_id": result.inserted_id})
        created["_id"] = str(created["_id"])
        return created
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not create citizen: {str(e)}")

@router.get("/")
async def list_citizens(limit: int = 20, skip: int = 0):
    citizens = list(db.citizens.find().skip(skip).limit(limit))
    for c in citizens:
        c["_id"] = str(c["_id"])
    return citizens

@router.get("/{citizen_id}")
async def get_citizen(citizen_id: str):
    if not ObjectId.is_valid(citizen_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
        
    citizen = db.citizens.find_one({"_id": ObjectId(citizen_id)})
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")
    
    citizen["_id"] = str(citizen["_id"])
    
    # Get citizen's requests
    requests = list(db.service_requests.find({"citizen_id": citizen_id}))
    citizen["requests"] = [{"request_id": r["request_id"], "status": r["status"], "category": r["category"]} for r in requests]
    
    return citizen

@router.post("/{citizen_id}/verify")
async def verify_citizen(citizen_id: str, otp_code: str = Body(..., embed=True)):
    """Stub OTP verification - accepts any 6-digit code"""
    if not ObjectId.is_valid(citizen_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    citizen = db.citizens.find_one({"_id": ObjectId(citizen_id)})
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")
    
    # Stub: Accept any 6-digit code
    if len(otp_code) == 6 and otp_code.isdigit():
        db.citizens.update_one(
            {"_id": ObjectId(citizen_id)},
            {"$set": {
                "verification_state": CitizenVerificationState.VERIFIED,
                "verified_at": datetime.utcnow()
            }}
        )
        return {"message": "Citizen verified successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code")

@router.post("/login")
async def login_citizen(email: str = Body(...), password: str = Body(...)):
    """Simple login - returns citizen data if credentials match"""
    citizen = db.citizens.find_one({"contacts.email": email})
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")
    
    # Simple password check (in production, use proper hashing)
    if citizen.get("password") != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    citizen["_id"] = str(citizen["_id"])
    del citizen["password"]  # Don't return password
    return citizen
