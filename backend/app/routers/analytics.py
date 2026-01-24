from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response
from typing import Optional, List
from datetime import datetime, timedelta
import io
import csv
from app.database import get_database

router = APIRouter(prefix="/analytics", tags=["Analytics"])
db = get_database()

def get_base_filters(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    zone: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    agent_id: Optional[str] = None
):
    query = {}
    if start_date or end_date:
        date_q = {}
        if start_date: date_q["$gte"] = start_date
        if end_date: date_q["$lte"] = end_date
        query["timestamps.created_at"] = date_q
    
    if zone: query["location.zone_id"] = zone
    if category: query["category"] = category
    if priority: query["priority"] = priority
    if agent_id: query["assigned_agent_id"] = agent_id
    
    return query

@router.get("/kpis")
async def get_kpis(
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None,
    zone: Optional[str] = None
):
    """
    Advanced KPIs using $facet for multi-dimensional analysis.
    Computes backlog, SLA metrics, and rating distributions in one pass.
    """
    now = datetime.utcnow()
    match_query = get_base_filters(start_date, end_date, zone)
    
    pipeline = [
        {"$match": match_query},
        {"$facet": {
            "overall": [
                {"$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "open": {"$sum": {"$cond": [{"$in": ["$status", ["new", "triaged", "assigned", "in_progress"]]}, 1, 0]}},
                    "avg_rating": {"$avg": "$rating.stars"}
                }}
            ],
            "by_status": [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ],
            "by_category": [
                {"$group": {"_id": "$category", "count": {"$sum": 1}}}
            ],
            "rating_dist": [
                {"$match": {"rating.stars": {"$ne": None}}},
                {"$group": {"_id": "$rating.stars", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}}
            ],
            "sla_data": [
                {"$match": {"status": {"$in": ["new", "triaged", "assigned", "in_progress"]}}},
                {"$project": {
                    "age_hours": {"$divide": [{"$subtract": [now, "$timestamps.created_at"]}, 3600000]},
                    "target": {"$ifNull": ["$sla_policy.target_hours", 72]},
                    "breach": {"$ifNull": ["$sla_policy.breach_threshold_hours", 120]}
                }},
                {"$group": {
                    "_id": None,
                    "at_risk": {"$sum": {"$cond": [{"$and": [{"$gte": ["$age_hours", "$target"]}, {"$lt": ["$age_hours", "$breach"]}]}, 1, 0]}},
                    "breached": {"$sum": {"$cond": [{"$gte": ["$age_hours", "$breach"]}, 1, 0]}}
                }}
            ]
        }}
    ]
    
    results = list(db.service_requests.aggregate(pipeline))[0]
    overall = results["overall"][0] if results["overall"] else {"total": 0, "open": 0, "avg_rating": 0}
    sla = results["sla_data"][0] if results["sla_data"] else {"at_risk": 0, "breached": 0}
    
    open_count = overall["open"]
    breached_count = sla["breached"]
    sla_breach_pct = (breached_count / open_count * 100) if open_count > 0 else 0

    return {
        "total_requests": overall["total"],
        "open_requests": open_count,
        "at_risk_count": sla["at_risk"],
        "breached_count": breached_count,
        "sla_breach_percentage": round(sla_breach_pct, 1),
        "avg_rating": round(overall.get("avg_rating") or 0, 1),
        "by_status": {r["_id"]: r["count"] for r in results["by_status"]},
        "by_category": {r["_id"]: r["count"] for r in results["by_category"]},
        "rating_distribution": {int(r["_id"]): r["count"] for r in results["rating_dist"]}
    }

@router.get("/heatmap")
async def get_heatmap_feed(category: Optional[str] = None, priority: Optional[str] = None):
    """GeoJSON FeatureCollection with normalized weights for heatmap"""
    query = {"status": {"$in": ["new", "triaged", "assigned", "in_progress"]}}
    if category: query["category"] = category
    if priority: query["priority"] = priority
    
    requests = list(db.service_requests.find(query))
    now = datetime.utcnow()
    features = []
    
    for req in requests:
        created = req["timestamps"].get("created_at", now)
        age_hours = (now - created).total_seconds() / 3600
        priority_weight = {"critical": 1.2, "high": 1.0, "medium": 0.7, "low": 0.4}.get(req.get("priority"), 0.7)
        weight = priority_weight * (1 + min(age_hours / 168, 2.0)) # Cap age weight at 1 week
        
        features.append({
            "type": "Feature",
            "properties": {
                "request_id": req["request_id"],
                "category": req["category"],
                "status": req["status"],
                "weight": round(weight, 2)
            },
            "geometry": req["location"]
        })
    return {"type": "FeatureCollection", "features": features}

@router.get("/cohorts")
async def get_cohorts():
    """Repeat-issue cohorts: identifying hotspots with frequent recurrence"""
    pipeline = [
        {"$group": {
            "_id": "$location.address_hint",
            "count": {"$sum": 1},
            "categories": {"$addToSet": "$category"},
            "avg_rating": {"$avg": "$rating.stars"},
            "last_incident": {"$max": "$timestamps.created_at"}
        }},
        {"$match": {"count": {"$gt": 1}}}, # Only cohorts with recurrence
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    results = list(db.service_requests.aggregate(pipeline))
    return results

@router.get("/agents")
async def get_agent_analytics():
    """Agent productivity and workload facets"""
    pipeline = [
        {"$lookup": {
            "from": "service_agents",
            "localField": "assigned_agent_id",
            "foreignField": "_id",
            "as": "agent_info"
        }},
        {"$match": {"assigned_agent_id": {"$ne": None}}},
        {"$group": {
            "_id": "$assigned_agent_id",
            "agent_name": {"$first": {"$arrayElemAt": ["$agent_info.name", 0]}},
            "active_tasks": {"$sum": {"$cond": [{"$in": ["$status", ["assigned", "in_progress"]]}, 1, 0]}},
            "completed_tasks": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}},
            "avg_resolution_hours": {"$avg": {
                "$divide": [
                    {"$subtract": ["$timestamps.resolved_at", "$timestamps.created_at"]},
                    3600000
                ]
            }}
        }},
        {"$sort": {"completed_tasks": -1}}
    ]
    return list(db.service_requests.aggregate(pipeline))

@router.get("/export/csv")
async def export_analytics_csv(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Generate governance-ready CSV report of SLA compliance"""
    query = get_base_filters(start_date, end_date)
    requests = list(db.service_requests.find(query).sort("timestamps.created_at", -1))
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Request ID", "Category", "Status", "Created At", "Resolved At", "SLA State", "Rating"])
    
    for req in requests:
        ts = req.get("timestamps", {})
        sla_state = "Compliant"
        if ts.get("created_at") and ts.get("resolved_at"):
            hours = (ts["resolved_at"] - ts["created_at"]).total_seconds() / 3600
            if hours > req.get("sla_policy", {}).get("breach_threshold_hours", 120):
                sla_state = "Breached"
        elif ts.get("created_at"):
            hours = (datetime.utcnow() - ts["created_at"]).total_seconds() / 3600
            if hours > req.get("sla_policy", {}).get("breach_threshold_hours", 120):
                sla_state = "Breached"
                
        rating_stars = ""
        if req.get("rating") and isinstance(req.get("rating"), dict):
            rating_stars = req.get("rating").get("stars", "")

        writer.writerow([
            req.get("request_id"),
            req.get("category"),
            req.get("status"),
            ts.get("created_at").isoformat() if ts.get("created_at") else "",
            ts.get("resolved_at").isoformat() if ts.get("resolved_at") else "",
            sla_state,
            rating_stars
        ])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cst_report_{datetime.now().strftime('%Y%m%d')}.csv"}
    )
