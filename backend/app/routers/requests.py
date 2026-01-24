from fastapi import APIRouter, HTTPException, Body, Query
from typing import List, Optional, Dict
from datetime import datetime
from bson import ObjectId
from app.database import get_database
from app.models.schemas import ServiceRequestCreate, RequestStatus, Priority
from app.utils.common import generate_request_id, get_allowed_transitions

router = APIRouter(prefix="/requests", tags=["Service Requests"])
db = get_database()

# SLA Policies based on priority
SLA_POLICIES = {
    "critical": {"target_hours": 24, "breach_threshold_hours": 36},
    "high": {"target_hours": 48, "breach_threshold_hours": 72},
    "medium": {"target_hours": 96, "breach_threshold_hours": 120},
    "low": {"target_hours": 168, "breach_threshold_hours": 240}
}

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
    new_request["request_id"] = req_id
    new_request["status"] = RequestStatus.NEW.value
    new_request["workflow"] = {
        "current_state": RequestStatus.NEW.value,
        "allowed_next": get_allowed_transitions(RequestStatus.NEW.value),
        "transition_rules_version": "v1.0"
    }
    
    # Assign SLA policy based on priority
    priority = request.priority.value if hasattr(request.priority, 'value') else request.priority
    sla = SLA_POLICIES.get(priority, SLA_POLICIES["medium"])
    new_request["sla_policy"] = {
        "policy_id": f"SLA-{priority.upper()}",
        "target_hours": sla["target_hours"],
        "breach_threshold_hours": sla["breach_threshold_hours"]
    }
    
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
                "meta": {"channel": "web", "anonymous": request.anonymous}
            }],
            "computed_kpis": {
                "resolution_minutes": None,
                "sla_target_hours": sla["target_hours"],
                "sla_state": "on_time",
                "escalation_count": 0
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
