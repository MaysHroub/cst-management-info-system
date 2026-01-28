from fastapi import APIRouter, HTTPException, Body, Query
from typing import List, Optional, Dict
from datetime import datetime
from bson import ObjectId
from app.database import get_database
from app.models.schemas import ServiceRequestCreate, RequestStatus, Priority
from app.utils.common import generate_request_id, get_allowed_transitions
import math

router = APIRouter(prefix="/requests", tags=["Service Requests"])
db = get_database()

# Valid categories
VALID_CATEGORIES = [
    "pothole", "water_leak", "trash", "lighting", 
    "sewage", "signage", "other"
]

# SLA Policies based on priority
SLA_POLICIES = {
    "critical": {"target_hours": 24, "breach_threshold_hours": 36},
    "high": {"target_hours": 48, "breach_threshold_hours": 72},
    "medium": {"target_hours": 96, "breach_threshold_hours": 120},
    "low": {"target_hours": 168, "breach_threshold_hours": 240}
}

# High-impact locations (schools, hospitals, etc.)
# Format: [longitude, latitude, name, type]
SENSITIVE_LOCATIONS = [
    {"coordinates": [35.2137, 31.7683], "name": "Hadassah Hospital", "type": "hospital"},
    {"coordinates": [35.1936, 31.7872], "name": "Shaare Zedek Medical Center", "type": "hospital"},
    {"coordinates": [35.2433, 31.7890], "name": "Hebrew University", "type": "school"},
    {"coordinates": [35.2044, 31.7752], "name": "Jerusalem College", "type": "school"},
    {"coordinates": [35.2167, 31.7778], "name": "Bezalel Academy", "type": "school"},
]

def calculate_distance(lon1, lat1, lon2, lat2):
    """Calculate distance in km between two coordinates using Haversine formula"""
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def check_high_impact_location(coordinates):
    """Check if location is near sensitive areas (schools, hospitals)"""
    lon, lat = coordinates
    proximity_threshold_km = 0.5  # 500 meters
    
    nearby_sensitive = []
    for loc in SENSITIVE_LOCATIONS:
        distance = calculate_distance(lon, lat, loc["coordinates"][0], loc["coordinates"][1])
        if distance <= proximity_threshold_km:
            nearby_sensitive.append({
                "name": loc["name"],
                "type": loc["type"],
                "distance_km": round(distance, 3)
            })
    
    return nearby_sensitive

def compute_triage(request_data):
    # Advanced triage logic: validate category, check high-impact, adjust priority
    category = request_data.get("category", "").lower()
    priority = request_data.get("priority", "medium").lower()
    location = request_data.get("location", {})
    
    # 1. Validate category
    if category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid category '{category}'. Must be one of: {', '.join(VALID_CATEGORIES)}"
        )
    
    # 2. Check for high-impact location
    high_impact_flag = False
    nearby_sensitive = []
    escalation_reason = None
    
    if location and location.get("coordinates"):
        nearby_sensitive = check_high_impact_location(location["coordinates"])
        
        if nearby_sensitive:
            high_impact_flag = True
            # Auto-escalate priority if near sensitive locations
            if priority in ["low", "medium"]:
                escalation_reason = f"Near {nearby_sensitive[0]['type']}: {nearby_sensitive[0]['name']}"
                priority = "high"  # Escalate to high
            elif priority == "high":
                # Already high, escalate to critical if near hospital
                if any(loc["type"] == "hospital" for loc in nearby_sensitive):
                    escalation_reason = f"Near hospital: {nearby_sensitive[0]['name']}"
                    priority = "critical"
    
    # 3. Compute SLA policy based on final priority
    sla = SLA_POLICIES.get(priority, SLA_POLICIES["medium"])
    
    triage_result = {
        "validated_category": category,
        "final_priority": priority,
        "original_priority": request_data.get("priority", "medium").lower(),
        "priority_escalated": priority != request_data.get("priority", "medium").lower(),
        "escalation_reason": escalation_reason,
        "high_impact_flag": high_impact_flag,
        "nearby_sensitive_locations": nearby_sensitive,
        "sla_policy": {
            "policy_id": f"SLA-{priority.upper()}",
            "target_hours": sla["target_hours"],
            "breach_threshold_hours": sla["breach_threshold_hours"]
        }
    }
    
    return triage_result

def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return doc

@router.post("/")
async def create_request(request: ServiceRequestCreate):
    count = db.service_requests.count_documents({}) + 1
    req_id = generate_request_id(count)
    
    new_request = request.dict()
    
    # advanced triage logic
    triage_result = compute_triage(new_request)
    
    # triaged priority and SLA policy
    new_request["request_id"] = req_id
    new_request["status"] = RequestStatus.NEW.value
    new_request["priority"] = triage_result["final_priority"]
    new_request["category"] = triage_result["validated_category"]
    
    # save triage metadata
    new_request["triage_metadata"] = {
        "original_priority": triage_result["original_priority"],
        "priority_escalated": triage_result["priority_escalated"],
        "escalation_reason": triage_result["escalation_reason"],
        "high_impact_flag": triage_result["high_impact_flag"],
        "nearby_sensitive_locations": triage_result["nearby_sensitive_locations"],
        "triaged_at": datetime.utcnow()
    }
    
    new_request["workflow"] = {
        "current_state": RequestStatus.NEW.value,
        "allowed_next": get_allowed_transitions(RequestStatus.NEW.value),
        "transition_rules_version": "v1.0"
    }
    
    # Use computed SLA policy
    new_request["sla_policy"] = triage_result["sla_policy"]
    
    new_request["timestamps"] = {
        "created_at": datetime.utcnow(),
        "triaged_at": None,
        "assigned_at": None,
        "resolved_at": None,
        "closed_at": None,
        "updated_at": datetime.utcnow()
    }
    new_request["comments"] = []
    new_request["rating"] = None
    new_request["milestones"] = []
    
    result = db.service_requests.insert_one(new_request)
    created_request = db.service_requests.find_one({"_id": result.inserted_id})
    
    # Log to performance_logs
    try:
        db.performance_logs.insert_one({
            "request_id": req_id,
            "event_stream": [{
                "type": "created",
                "by": {"actor_type": "citizen", "actor_id": request.citizen_id},
                "at": datetime.utcnow(),
                "meta": {
                    "channel": "web", 
                    "anonymous": request.anonymous,
                    "auto_triaged": True,
                    "priority_escalated": triage_result["priority_escalated"]
                }
            }],
            "computed_kpis": {
                "resolution_minutes": None,
                "sla_target_hours": triage_result["sla_policy"]["target_hours"],
                "sla_state": "on_time",
                "escalation_count": 1 if triage_result["priority_escalated"] else 0
            },
            "citizen_feedback": None
        })
    except Exception as e:
        print(f"Performance log error: {e}")
    
    return serialize_doc(created_request)

@router.get("/")
async def list_requests(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    agent_id: Optional[str] = None,
    citizen_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if priority:
        query["priority"] = priority
    if agent_id:
        query["assigned_agent_id"] = agent_id
    if citizen_id:
        query["citizen_id"] = citizen_id
        
    requests = list(db.service_requests.find(query).sort("timestamps.created_at", -1).skip(skip).limit(limit))
    return [serialize_doc(r) for r in requests]

@router.get("/{request_id}")
async def get_request(request_id: str):
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return serialize_doc(req)

@router.post("/{request_id}/triage")
async def manual_triage_request(request_id: str, override_priority: Optional[str] = Body(None)):
    """Manually re-triage a request with advanced logic"""
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Run triage logic
    triage_result = compute_triage(req)
    
    # If staff overrides priority, use that instead
    if override_priority:
        if override_priority.lower() not in ["low", "medium", "high", "critical"]:
            raise HTTPException(status_code=400, detail="Invalid priority override")
        triage_result["final_priority"] = override_priority.lower()
        triage_result["priority_escalated"] = True
        triage_result["escalation_reason"] = "Manual override by staff"
        # Recompute SLA
        sla = SLA_POLICIES.get(override_priority.lower(), SLA_POLICIES["medium"])
        triage_result["sla_policy"] = {
            "policy_id": f"SLA-{override_priority.upper()}",
            "target_hours": sla["target_hours"],
            "breach_threshold_hours": sla["breach_threshold_hours"]
        }
    
    # Update request
    update_data = {
        "priority": triage_result["final_priority"],
        "sla_policy": triage_result["sla_policy"],
        "triage_metadata": {
            "original_priority": req.get("priority", "medium"),
            "priority_escalated": triage_result["priority_escalated"],
            "escalation_reason": triage_result["escalation_reason"],
            "high_impact_flag": triage_result["high_impact_flag"],
            "nearby_sensitive_locations": triage_result["nearby_sensitive_locations"],
            "triaged_at": datetime.utcnow(),
            "manual_triage": override_priority is not None
        },
        "timestamps.triaged_at": datetime.utcnow(),
        "timestamps.updated_at": datetime.utcnow()
    }
    
    db.service_requests.update_one(
        {"request_id": request_id},
        {"$set": update_data}
    )
    
    updated_req = db.service_requests.find_one({"request_id": request_id})
    return {
        "message": "Request triaged successfully",
        "triage_result": triage_result,
        "request": serialize_doc(updated_req)
    }

@router.patch("/{request_id}/transition")
async def transition_request(request_id: str, new_status: str = Body(..., embed=True)):
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    current_status = req["status"]
    allowed = get_allowed_transitions(current_status)
    
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid transition from {current_status} to {new_status}. Allowed: {allowed}")
    
    update_data = {
        "status": new_status,
        "workflow.current_state": new_status,
        "workflow.allowed_next": get_allowed_transitions(new_status),
        "timestamps.updated_at": datetime.utcnow()
    }
    
    if new_status == "triaged":
        update_data["timestamps.triaged_at"] = datetime.utcnow()
    elif new_status == "assigned":
        update_data["timestamps.assigned_at"] = datetime.utcnow()
    elif new_status == "resolved":
        update_data["timestamps.resolved_at"] = datetime.utcnow()
    elif new_status == "closed":
        update_data["timestamps.closed_at"] = datetime.utcnow()

    db.service_requests.update_one({"request_id": request_id}, {"$set": update_data})
    
    # Log event
    try:
        db.performance_logs.update_one(
            {"request_id": request_id},
            {"$push": {"event_stream": {
                "type": new_status,
                "by": {"actor_type": "staff", "actor_id": "system"},
                "at": datetime.utcnow(),
                "meta": {}
            }}}
        )
    except Exception as e:
        print(f"Performance log error: {e}")
    
    return serialize_doc(db.service_requests.find_one({"request_id": request_id}))

@router.post("/{request_id}/comment")
async def add_comment(
    request_id: str, 
    text: str = Body(...), 
    author_id: str = Body(...),
    author_type: str = Body("citizen")
):
    """Add a comment to a request - threaded comments for citizen interaction"""
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    comment = {
        "id": str(ObjectId()),
        "text": text,
        "author_id": author_id,
        "author_type": author_type,
        "created_at": datetime.utcnow()
    }
    
    db.service_requests.update_one(
        {"request_id": request_id},
        {
            "$push": {"comments": comment},
            "$set": {"timestamps.updated_at": datetime.utcnow()}
        }
    )
    
    return {"message": "Comment added", "comment": comment}

@router.post("/{request_id}/rating")
async def rate_request(
    request_id: str, 
    stars: int = Body(..., ge=1, le=5), 
    comment: str = Body(None),
    reason_codes: List[str] = Body([]),
    dispute: bool = Body(False),
    dispute_reason: str = Body(None)
):
    """Rate a resolved/closed request with optional dispute flagging"""
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req["status"] not in ["resolved", "closed"]:
        raise HTTPException(status_code=400, detail="Can only rate resolved/closed requests")
    
    rating = {
        "stars": stars,
        "comment": comment,
        "reason_codes": reason_codes,
        "dispute": dispute,
        "dispute_reason": dispute_reason,
        "created_at": datetime.utcnow()
    }
    
    db.service_requests.update_one(
        {"request_id": request_id},
        {"$set": {"rating": rating, "timestamps.updated_at": datetime.utcnow()}}
    )
    
    # Update performance log
    try:
        db.performance_logs.update_one(
            {"request_id": request_id},
            {"$set": {"citizen_feedback": rating}}
        )
    except Exception as e:
        print(f"Performance log error: {e}")
    
    return {"message": "Rating submitted", "rating": rating}

@router.post("/{request_id}/evidence")
async def add_evidence(
    request_id: str,
    evidence_type: str = Body("photo"),
    url: str = Body(...)
):
    """Add additional evidence to a request"""
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    evidence = {
        "type": evidence_type,
        "url": url,
        "uploaded_at": datetime.utcnow()
    }
    
    db.service_requests.update_one(
        {"request_id": request_id},
        {
            "$push": {"evidence": evidence},
            "$set": {"timestamps.updated_at": datetime.utcnow()}
        }
    )
    
    return {"message": "Evidence added", "evidence": evidence}

@router.patch("/{request_id}/milestone")
async def add_milestone(
    request_id: str, 
    milestone_type: str = Body(...), 
    notes: str = Body(None),
    evidence: List[Dict[str, str]] = Body([])
):
    """Add milestone: arrived, work_started, resolved"""
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    valid_milestones = ["arrived", "work_started", "resolved"]
    if milestone_type not in valid_milestones:
        raise HTTPException(status_code=400, detail=f"Invalid milestone. Use: {valid_milestones}")
    
    milestone = {
        "type": milestone_type,
        "timestamp": datetime.utcnow(),
        "notes": notes,
        "evidence": evidence
    }
    
    update = {"$push": {"milestones": milestone}, "$set": {"timestamps.updated_at": datetime.utcnow()}}
    
    # Auto-transition status based on milestone
    if milestone_type == "arrived" or milestone_type == "work_started":
        update["$set"]["status"] = "in_progress"
        update["$set"]["workflow.current_state"] = "in_progress"
    elif milestone_type == "resolved":
        update["$set"]["status"] = "resolved"
        update["$set"]["workflow.current_state"] = "resolved"
        update["$set"]["timestamps.resolved_at"] = datetime.utcnow()
    
    db.service_requests.update_one({"request_id": request_id}, update)
    
    return {"message": f"Milestone '{milestone_type}' added"}

@router.post("/{request_id}/escalate")
async def escalate_request(request_id: str, reason: str = Body(...)):
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Log escalation event
    try:
        db.performance_logs.update_one(
            {"request_id": request_id},
            {
                "$push": {"event_stream": {
                    "type": "escalation",
                    "by": {"actor_type": "system", "actor_id": "manual"},
                    "at": datetime.utcnow(),
                    "meta": {"reason": reason}
                }},
                "$inc": {"computed_kpis.escalation_count": 1}
            }
        )
    except Exception as e:
        print(f"Performance log error: {e}")
    
    return {"message": "Request escalated", "reason": reason}

@router.get("/sla/at-risk")
async def get_sla_at_risk_requests():
    """Get all requests that are at risk of SLA breach or have breached SLA"""
    now = datetime.utcnow()
    
    # Find all open requests
    requests = list(db.service_requests.find({
        "status": {"$in": ["new", "triaged", "assigned", "in_progress"]}
    }))
    
    at_risk = []
    breached = []
    
    for req in requests:
        created_at = req["timestamps"]["created_at"]
        age_hours = (now - created_at).total_seconds() / 3600
        
        sla_policy = req.get("sla_policy", {})
        target_hours = sla_policy.get("target_hours", 72)
        breach_hours = sla_policy.get("breach_threshold_hours", 120)
        
        req_data = {
            "request_id": req["request_id"],
            "priority": req.get("priority", "medium"),
            "category": req.get("category"),
            "status": req["status"],
            "age_hours": round(age_hours, 1),
            "target_hours": target_hours,
            "breach_hours": breach_hours,
            "time_remaining": round(breach_hours - age_hours, 1),
            "created_at": created_at,
            "assigned_agent_id": req.get("assigned_agent_id")
        }
        
        if age_hours >= breach_hours:
            req_data["sla_state"] = "breached"
            breached.append(req_data)
        elif age_hours >= target_hours:
            req_data["sla_state"] = "at_risk"
            at_risk.append(req_data)
    
    return {
        "at_risk_count": len(at_risk),
        "breached_count": len(breached),
        "at_risk_requests": sorted(at_risk, key=lambda x: x["time_remaining"]),
        "breached_requests": sorted(breached, key=lambda x: x["age_hours"], reverse=True),
        "total_flagged": len(at_risk) + len(breached)
    }

@router.get("/{request_id}/sla-status")
async def get_request_sla_status(request_id: str):
    """Get SLA status for a specific request
        1. Calculate age: current_time - created_at (in hours)

        2. For open requests:
        - on_time: age < target_hours
        - at_risk: age >= target_hours AND age < breach_hours
        - breached: age >= breach_hours

        3. For resolved requests:
        - Calculate resolution_time: resolved_at - created_at
        - Compare against target_hours

        4. Return:
        - sla_state (on_time/at_risk/breached)
        - age_hours, target_hours, breach_hours
        - time_remaining_to_breach (can be negative if overdue)
    """
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req["status"] in ["resolved", "closed"]:
        resolved_at = req["timestamps"].get("resolved_at")
        created_at = req["timestamps"]["created_at"]
        if resolved_at:
            resolution_hours = (resolved_at - created_at).total_seconds() / 3600
            sla_policy = req.get("sla_policy", {})
            target_hours = sla_policy.get("target_hours", 72)
            
            return {
                "request_id": request_id,
                "status": "resolved",
                "resolution_hours": round(resolution_hours, 1),
                "target_hours": target_hours,
                "sla_met": resolution_hours <= target_hours,
                "resolved_at": resolved_at
            }
    
    # For open requests
    now = datetime.utcnow()
    created_at = req["timestamps"]["created_at"]
    age_hours = (now - created_at).total_seconds() / 3600
    
    sla_policy = req.get("sla_policy", {})
    target_hours = sla_policy.get("target_hours", 72)
    breach_hours = sla_policy.get("breach_threshold_hours", 120)
    
    if age_hours >= breach_hours:
        sla_state = "breached"
    elif age_hours >= target_hours:
        sla_state = "at_risk"
    else:
        sla_state = "on_time"
    
    return {
        "request_id": request_id,
        "status": req["status"],
        "age_hours": round(age_hours, 1),
        "target_hours": target_hours,
        "breach_hours": breach_hours,
        "time_remaining_to_breach": round(breach_hours - age_hours, 1),
        "sla_state": sla_state,
        "priority": req.get("priority", "medium")
    }

@router.post("/{request_id}/resolve")
async def resolve_request(
    request_id: str,
    resolution_notes: str = Body(...),
    evidence_urls: List[str] = Body([]),
    resolved_by: str = Body(...)
):
    """Mark a request as resolved with evidence and notes"""
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req["status"] not in ["assigned", "in_progress"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Can only resolve requests in 'assigned' or 'in_progress' status. Current status: {req['status']}"
        )
    
    now = datetime.utcnow()
    
    # Add resolution milestone with evidence
    milestone = {
        "type": "resolved",
        "timestamp": now,
        "notes": resolution_notes,
        "evidence": [{"type": "photo", "url": url, "uploaded_at": now} for url in evidence_urls],
        "resolved_by": resolved_by
    }
    
    # Calculate resolution time
    created_at = req["timestamps"]["created_at"]
    resolution_hours = (now - created_at).total_seconds() / 3600
    sla_policy = req.get("sla_policy", {})
    target_hours = sla_policy.get("target_hours", 72)
    sla_met = resolution_hours <= target_hours
    
    # Update request
    update_data = {
        "status": "resolved",
        "workflow.current_state": "resolved",
        "workflow.allowed_next": ["closed"],
        "timestamps.resolved_at": now,
        "timestamps.updated_at": now,
        "resolution": {
            "notes": resolution_notes,
            "resolved_by": resolved_by,
            "resolved_at": now,
            "resolution_hours": round(resolution_hours, 1),
            "sla_met": sla_met
        }
    }
    
    db.service_requests.update_one(
        {"request_id": request_id},
        {
            "$set": update_data,
            "$push": {"milestones": milestone}
        }
    )
    
    # Update performance log
    try:
        db.performance_logs.update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "computed_kpis.resolution_minutes": int(resolution_hours * 60),
                    "computed_kpis.sla_state": "met" if sla_met else "breached"
                },
                "$push": {"event_stream": {
                    "type": "resolved",
                    "by": {"actor_type": "agent", "actor_id": resolved_by},
                    "at": now,
                    "meta": {"resolution_hours": round(resolution_hours, 1), "sla_met": sla_met}
                }}
            }
        )
    except Exception as e:
        print(f"Performance log error: {e}")
    
    return {
        "message": "Request marked as resolved",
        "request_id": request_id,
        "resolution_hours": round(resolution_hours, 1),
        "sla_met": sla_met,
        "target_hours": target_hours
    }

