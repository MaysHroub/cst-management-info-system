from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.database import get_database
from app.models.schemas import CitizenCreate, CitizenVerificationState

router = APIRouter(prefix="/citizens", tags=["Citizens"])
db = get_database()

def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    # Remove password from response
    if "password" in doc:
        del doc["password"]
    return doc

@router.post("/")
async def create_citizen(citizen: CitizenCreate):
    """Create a new citizen profile with verification state and preferences"""
    # Check if email exists
    if citizen.contacts.email:
        existing = db.citizens.find_one({"contacts.email": citizen.contacts.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
            
    new_citizen = citizen.dict()
    new_citizen["verification_state"] = CitizenVerificationState.UNVERIFIED.value
    new_citizen["created_at"] = datetime.utcnow()
    new_citizen["stats"] = {"total_requests": 0, "avg_rating": 0}
    
    # Set default preferences if not provided
    if not new_citizen.get("preferences"):
        new_citizen["preferences"] = {
            "notifications": {
                "on_status_change": True,
                "on_resolution": True,
                "email_enabled": True,
                "sms_enabled": False
            },
            "privacy": {
                "default_anonymous": False,
                "share_publicly_on_map": True
            },
            "language": "en"
        }
    
    try:
        result = db.citizens.insert_one(new_citizen)
        created = db.citizens.find_one({"_id": result.inserted_id})
        return serialize_doc(created)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not create citizen: {str(e)}")

@router.get("/")
async def list_citizens(limit: int = 20, skip: int = 0):
    """List all citizens"""
    citizens = list(db.citizens.find().skip(skip).limit(limit))
    return [serialize_doc(c) for c in citizens]

@router.get("/{citizen_id}")
async def get_citizen(citizen_id: str):
    """Retrieve citizen profile with summary KPIs"""
    if not ObjectId.is_valid(citizen_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
        
    citizen = db.citizens.find_one({"_id": ObjectId(citizen_id)})
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")
    
    # Get citizen's requests for KPIs
    requests = list(db.service_requests.find({"citizen_id": citizen_id}))
    
    # Calculate stats
    total_requests = len(requests)
    resolved_requests = [r for r in requests if r.get("status") in ["resolved", "closed"]]
    ratings = [r.get("rating", {}).get("stars") for r in resolved_requests if r.get("rating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    citizen["stats"] = {
        "total_requests": total_requests,
        "open_requests": len([r for r in requests if r.get("status") not in ["resolved", "closed"]]),
        "resolved_requests": len(resolved_requests),
        "avg_rating": round(avg_rating, 1)
    }
    
    # Add recent requests summary
    citizen["recent_requests"] = [
        {
            "request_id": r["request_id"],
            "category": r.get("category"),
            "status": r.get("status"),
            "created_at": r.get("timestamps", {}).get("created_at")
        } 
        for r in requests[:5]
    ]
    
    return serialize_doc(citizen)

@router.post("/{citizen_id}/verify")
async def verify_citizen(citizen_id: str, otp_code: str = Body(..., embed=True)):
    """Verify citizen account using OTP stub (accepts any 6-digit code)"""
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
                "verification_state": CitizenVerificationState.VERIFIED.value,
                "verified_at": datetime.utcnow()
            }}
        )
        return {"message": "Citizen verified successfully", "verification_state": "verified"}
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code. Must be 6 digits.")

@router.post("/login")
async def login_citizen(email: str = Body(...), password: str = Body(...)):
    """Login citizen - returns citizen data if credentials match"""
    citizen = db.citizens.find_one({"contacts.email": email})
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")
    
    # Simple password check (in production, use proper hashing)
    if citizen.get("password") != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return serialize_doc(citizen)

@router.patch("/{citizen_id}/preferences")
async def update_preferences(
    citizen_id: str,
    notifications: dict = Body(None),
    privacy: dict = Body(None),
    language: str = Body(None)
):
    """Update citizen notification and privacy preferences"""
    if not ObjectId.is_valid(citizen_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    citizen = db.citizens.find_one({"_id": ObjectId(citizen_id)})
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")
    
    update = {}
    if notifications:
        for key, value in notifications.items():
            update[f"preferences.notifications.{key}"] = value
    if privacy:
        for key, value in privacy.items():
            update[f"preferences.privacy.{key}"] = value
    if language:
        update["preferences.language"] = language
    
    if update:
        db.citizens.update_one({"_id": ObjectId(citizen_id)}, {"$set": update})
    
    return {"message": "Preferences updated"}

@router.get("/{citizen_id}/requests")
async def get_citizen_requests(citizen_id: str, status: Optional[str] = None):
    """Get all requests submitted by a citizen"""
    if not ObjectId.is_valid(citizen_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    query = {"citizen_id": citizen_id}
    if status:
        query["status"] = status
    
    requests = list(db.service_requests.find(query).sort("timestamps.created_at", -1))
    
    # Serialize each request
    result = []
    for r in requests:
        r["_id"] = str(r["_id"])
        result.append(r)
    
    return result
