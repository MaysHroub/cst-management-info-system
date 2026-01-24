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
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        # Auto-assignment based on geo coverage + skills + shift
        # 1. Geo Coverage
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
        
        # 3. Shift Availability
        # Use local time for shift comparison as shifts are likely defined in local time
        now = datetime.now()
        current_day = now.strftime("%a") # Mon, Tue...
        current_time = now.strftime("%H:%M")
        
        print(f"Auto-Assign Debug: Request {request_id} (Category: {req.get('category')}) at {location}")
        print(f"Current Time: {current_day} {current_time}")
        print(f"Initial Candidates: {[c['name'] for c in candidates]}")
        
        # Filter by Skill
        CATEGORY_SKILLS = {
            "pothole": "road",
            "signage": "road",
            "lighting": "road",
            "water_leak": "water",
            "sewage": "water",
            "trash": "waste"
        }
        required_skill = CATEGORY_SKILLS.get(req.get("category"), "general")
        skill_candidates = []
        for c in candidates:
            if required_skill in c.get("skills", []) or "general" in c.get("skills", []):
                skill_candidates.append(c)
            else:
                print(f"Candidate {c['name']} rejected: Missing skill '{required_skill}'")
        
        if skill_candidates:
            candidates = skill_candidates
        
        # Filter by Shift
        shift_candidates = []
        for c in candidates:
            is_available = False
            schedule = c.get("schedule", {})
            if schedule.get("on_call", False):
                is_available = True
            else:
                for shift in schedule.get("shifts", []):
                    if shift["day"] == current_day:
                        if shift["start"] <= current_time <= shift["end"]:
                            is_available = True
                            break
            
            if is_available:
                shift_candidates.append(c)
            else:
                print(f"Candidate {c['name']} rejected: Not on shift (Schedule: {schedule.get('shifts')})")
        
        if shift_candidates:
            candidates = shift_candidates
        else:
            print("No candidates on shift. Checking if any logic fallback is needed. Currently Strict.")
        
        if not candidates:
            print("No agents available after filtering.")
            raise HTTPException(status_code=404, detail="No agents available matching criteria (Zone+Skill+Shift)")
        
        # 4. Workload Balancing
        for c in candidates:
            c["_workload"] = db.service_requests.count_documents({
                "assigned_agent_id": str(c["_id"]),
                "status": {"$in": ["assigned", "in_progress"]}
            })
        
        chosen_agent = min(candidates, key=lambda x: x["_workload"])
        print(f"Chosen Agent: {chosen_agent['name']} (Workload: {chosen_agent['_workload']})")
    
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
