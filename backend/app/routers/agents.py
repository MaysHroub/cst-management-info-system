from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.database import get_database
from app.models.schemas import Agent, AgentCreate, RequestStatus
from app.utils.common import get_allowed_transitions

router = APIRouter(prefix="/agents", tags=["Service Agents"])
db = get_database()

@router.post("/")
async def create_agent(agent: AgentCreate):
    # Check if agent_code exists
    existing = db.service_agents.find_one({"agent_code": agent.agent_code})
    if existing:
        raise HTTPException(status_code=400, detail="Agent code already exists")
    
    new_agent = agent.dict()
    new_agent["created_at"] = datetime.utcnow()
    new_agent["active"] = True
    new_agent["current_workload"] = 0
    
    result = db.service_agents.insert_one(new_agent)
    created = db.service_agents.find_one({"_id": result.inserted_id})
    created["_id"] = str(created["_id"])
    return created

@router.get("/")
async def list_agents(active_only: bool = True):
    query = {"active": True} if active_only else {}
    agents = list(db.service_agents.find(query))
    for a in agents:
        a["_id"] = str(a["_id"])
        # Calculate current workload
        a["current_workload"] = db.service_requests.count_documents({
            "assigned_agent_id": str(a["_id"]),
            "status": {"$in": ["assigned", "in_progress"]}
        })
    return agents

@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    agent = db.service_agents.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent["_id"] = str(agent["_id"])
    
    # Get assigned requests
    requests = list(db.service_requests.find({"assigned_agent_id": agent_id}))
    agent["assigned_requests"] = [{
        "request_id": r["request_id"],
        "status": r["status"],
        "category": r["category"],
        "priority": r.get("priority"),
        "location": r.get("location")
    } for r in requests]
    
    agent["current_workload"] = len([r for r in requests if r["status"] in ["assigned", "in_progress"]])
    agent["completed_count"] = len([r for r in requests if r["status"] in ["resolved", "closed"]])
    
    return agent

@router.get("/{agent_id}/tasks")
async def get_agent_tasks(agent_id: str):
    """Get active tasks for an agent"""
    tasks = list(db.service_requests.find({
        "assigned_agent_id": agent_id,
        "status": {"$in": ["assigned", "in_progress"]}
    }).sort("timestamps.assigned_at", -1))
    
    for t in tasks:
        t["_id"] = str(t["_id"])
    
    return tasks

@router.post("/assign-request/{request_id}")
async def assign_request_to_best_agent(request_id: str, agent_id: Optional[str] = None):
    """Auto-assign or manually assign a request to an agent"""
    req = db.service_requests.find_one({"request_id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req["status"] not in ["triaged", "assigned"]:
        raise HTTPException(status_code=400, detail="Request must be triaged first")

    location = req["location"]
    
    if agent_id:
        # Manual assignment
        if not ObjectId.is_valid(agent_id):
            raise HTTPException(status_code=400, detail="Invalid agent ID")
        chosen_agent = db.service_agents.find_one({"_id": ObjectId(agent_id), "active": True})
        if not chosen_agent:
            raise HTTPException(status_code=404, detail="Agent not found")
    else:
        # Auto-assignment based on geo coverage
        query = {
            "coverage.geo_fence": {
                "$geoIntersects": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": location["coordinates"]
                    }
                }
            },
            "active": True
        }
        
        candidates = list(db.service_agents.find(query))
        
        if not candidates:
            # Fallback: get any active agent
            candidates = list(db.service_agents.find({"active": True}).limit(5))
        
        if not candidates:
            raise HTTPException(status_code=404, detail="No agents available")
        
        # Simple workload balancing: pick agent with least active tasks
        for c in candidates:
            c["_workload"] = db.service_requests.count_documents({
                "assigned_agent_id": str(c["_id"]),
                "status": {"$in": ["assigned", "in_progress"]}
            })
        
        chosen_agent = min(candidates, key=lambda x: x["_workload"])
    
    # Update Request
    db.service_requests.update_one(
        {"request_id": request_id},
        {
            "$set": {
                "assigned_agent_id": str(chosen_agent["_id"]),
                "status": RequestStatus.ASSIGNED,
                "workflow.current_state": RequestStatus.ASSIGNED,
                "workflow.allowed_next": get_allowed_transitions(RequestStatus.ASSIGNED),
                "timestamps.assigned_at": datetime.utcnow(),
                "timestamps.updated_at": datetime.utcnow()
            }
        }
    )
    
    # Log event
    db.performance_logs.update_one(
        {"request_id": request_id},
        {"$push": {"event_stream": {
            "type": "assigned",
            "by": {"actor_type": "system", "actor_id": "auto_assign"},
            "at": datetime.utcnow(),
            "meta": {"agent_id": str(chosen_agent["_id"]), "agent_name": chosen_agent["name"]}
        }}}
    )
    
    return {"message": "Assigned successfully", "agent_id": str(chosen_agent["_id"]), "agent_name": chosen_agent["name"]}

@router.patch("/{agent_id}")
async def update_agent(agent_id: str, active: Optional[bool] = Body(None)):
    """Update agent status"""
    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    update = {"$set": {"updated_at": datetime.utcnow()}}
    if active is not None:
        update["$set"]["active"] = active
    
    db.service_agents.update_one({"_id": ObjectId(agent_id)}, update)
    
    return {"message": "Agent updated"}
