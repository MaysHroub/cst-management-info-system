from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_database

router = APIRouter(prefix="/analytics", tags=["Analytics"])
db = get_database()

@router.get("/stats")
async def get_stats():
    """Get overall statistics"""
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_results = list(db.service_requests.aggregate(pipeline))
    by_status = {r["_id"]: r["count"] for r in status_results}
    
    # Category breakdown
    cat_pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    cat_results = list(db.service_requests.aggregate(cat_pipeline))
    by_category = {r["_id"]: r["count"] for r in cat_results}
    
    # Priority breakdown
    prio_pipeline = [
        {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
    ]
    prio_results = list(db.service_requests.aggregate(prio_pipeline))
    by_priority = {r["_id"]: r["count"] for r in prio_results}
    
    total = db.service_requests.count_documents({})
    open_count = db.service_requests.count_documents({"status": {"$in": ["new", "triaged", "assigned", "in_progress"]}})
    resolved_count = db.service_requests.count_documents({"status": {"$in": ["resolved", "closed"]}})
    
    return {
        "total_requests": total,
        "open_requests": open_count,
        "resolved_requests": resolved_count,
        "by_status": by_status,
        "by_category": by_category,
        "by_priority": by_priority
    }

@router.get("/kpis")
async def get_kpis():
    """Get Key Performance Indicators"""
    total = db.service_requests.count_documents({})
    open_count = db.service_requests.count_documents({"status": {"$in": ["new", "triaged", "assigned", "in_progress"]}})
    
    # SLA breach calculation
    now = datetime.utcnow()
    at_risk = 0
    breached = 0
    
    open_requests = list(db.service_requests.find({"status": {"$in": ["new", "triaged", "assigned", "in_progress"]}}))
    for req in open_requests:
        created = req["timestamps"].get("created_at")
        if created:
            hours_elapsed = (now - created).total_seconds() / 3600
            sla = req.get("sla_policy", {})
            target = sla.get("target_hours", 96)
            breach = sla.get("breach_threshold_hours", 120)
            
            if hours_elapsed >= breach:
                breached += 1
            elif hours_elapsed >= target:
                at_risk += 1
    
    # Average resolution time
    resolved = list(db.service_requests.find({"status": {"$in": ["resolved", "closed"]}, "timestamps.resolved_at": {"$exists": True}}))
    resolution_times = []
    for req in resolved:
        created = req["timestamps"].get("created_at")
        resolved_at = req["timestamps"].get("resolved_at")
        if created and resolved_at:
            resolution_times.append((resolved_at - created).total_seconds() / 3600)
    
    avg_resolution_hours = sum(resolution_times) / len(resolution_times) if resolution_times else 0
    
    # Average rating
    ratings = list(db.service_requests.find({"rating": {"$ne": None}}))
    avg_rating = sum(r["rating"]["stars"] for r in ratings) / len(ratings) if ratings else 0
    
    sla_breach_pct = (breached / open_count * 100) if open_count > 0 else 0
    
    return {
        "total_requests": total,
        "open_requests": open_count,
        "at_risk_count": at_risk,
        "breached_count": breached,
        "sla_breach_percentage": round(sla_breach_pct, 1),
        "avg_resolution_hours": round(avg_resolution_hours, 1),
        "avg_rating": round(avg_rating, 1),
        "total_agents": db.service_agents.count_documents({"active": True}),
        "total_citizens": db.citizens.count_documents({})
    }

@router.get("/heatmap")
async def get_heatmap_feed(category: Optional[str] = None, priority: Optional[str] = None):
    """Return GeoJSON FeatureCollection for open requests"""
    query = {"status": {"$in": ["new", "triaged", "assigned", "in_progress"]}}
    if category:
        query["category"] = category
    if priority:
        query["priority"] = priority
    
    requests = list(db.service_requests.find(query))
    
    now = datetime.utcnow()
    features = []
    for req in requests:
        created = req["timestamps"].get("created_at", now)
        age_hours = (now - created).total_seconds() / 3600
        
        # Weight based on priority and age
        priority_weight = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3}.get(req.get("priority", "medium"), 0.5)
        weight = priority_weight * (1 + age_hours / 24)  # Older requests have more weight
        
        features.append({
            "type": "Feature",
            "properties": {
                "request_id": req["request_id"],
                "category": req.get("category"),
                "priority": req.get("priority"),
                "status": req.get("status"),
                "weight": round(weight, 2),
                "age_hours": round(age_hours, 1)
            },
            "geometry": req["location"]
        })
    
    return {
        "type": "FeatureCollection",
        "features": features,
        "generated_at": now.isoformat()
    }

@router.get("/agents")
async def get_agent_analytics():
    """Agent productivity analytics"""
    agents = list(db.service_agents.find({"active": True}))
    result = []
    
    for agent in agents:
        agent_id = str(agent["_id"])
        
        # Get assigned requests
        assigned = db.service_requests.count_documents({"assigned_agent_id": agent_id, "status": {"$in": ["assigned", "in_progress"]}})
        completed = db.service_requests.count_documents({"assigned_agent_id": agent_id, "status": {"$in": ["resolved", "closed"]}})
        total = db.service_requests.count_documents({"assigned_agent_id": agent_id})
        
        result.append({
            "agent_id": agent_id,
            "agent_name": agent["name"],
            "department": agent.get("department"),
            "active_tasks": assigned,
            "completed_tasks": completed,
            "total_tasks": total,
            "skills": agent.get("skills", [])
        })
    
    return result

@router.get("/timeline")
async def get_timeline(days: int = Query(7, ge=1, le=90)):
    """Get requests over time"""
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    
    pipeline = [
        {"$match": {"timestamps.created_at": {"$gte": start}}},
        {"$group": {
            "_id": {
                "$dateToString": {"format": "%Y-%m-%d", "date": "$timestamps.created_at"}
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    results = list(db.service_requests.aggregate(pipeline))
    return [{"date": r["_id"], "count": r["count"]} for r in results]

@router.get("/zones")
async def get_zone_stats():
    """Aggregate stats by zone"""
    pipeline = [
        {"$group": {
            "_id": "$location.zone_id",
            "count": {"$sum": 1},
            "open": {"$sum": {"$cond": [{"$in": ["$status", ["new", "triaged", "assigned", "in_progress"]]}, 1, 0]}},
            "resolved": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}}
        }},
        {"$sort": {"count": -1}}
    ]
    
    results = list(db.service_requests.aggregate(pipeline))
    return [{"zone_id": r["_id"] or "Unknown", "total": r["count"], "open": r["open"], "resolved": r["resolved"]} for r in results]
