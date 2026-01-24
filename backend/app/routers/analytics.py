from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import io
import csv
import time
from bson import ObjectId
from app.database import get_database

router = APIRouter(prefix="/analytics", tags=["Analytics"])
db = get_database()

# Simple Cache
CACHE = {}
CACHE_TTL = 300 # 5 minutes

def get_cached(key: str):
    if key in CACHE:
        val, ts = CACHE[key]
        if time.time() - ts < CACHE_TTL:
            return val
    return None

def set_cache(key: str, value: Any):
    CACHE[key] = (value, time.time())

def get_base_filters(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    zone: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    agent_id: Optional[str] = None,
    sla_state: Optional[str] = None
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
    
    if sla_state:
        # Complex calculation needed in aggregation, but for basic find/stats:
        now = datetime.utcnow()
        if sla_state == "breached":
            query["status"] = {"$in": ["new", "triaged", "assigned", "in_progress"]}
            # Logic: created_at < now - breach_threshold
            # Since breach_threshold varies by priority, this is tricky in a single find query.
            # We'll handle this in aggregation pipelines where possible.
            pass

    return query

@router.get("/kpis")
async def get_kpis(
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None,
    zone: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    agent_id: Optional[str] = None
):
    match_query = get_base_filters(start_date, end_date, zone, category, priority, agent_id)
    cache_key = f"kpis_{str(match_query)}"
    
    cached = get_cached(cache_key)
    if cached: return cached

    now = datetime.utcnow()
    pipeline = [
        {"$match": match_query},
        {"$facet": {
            "overall": [
                {"$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "open": {"$sum": {"$cond": [{"$in": ["$status", ["new", "triaged", "assigned", "in_progress"]]}, 1, 0]}},
                    "resolved": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}},
                    "avg_rating": {"$avg": "$rating.stars"}
                }}
            ],
            "by_status": [{"$group": {"_id": "$status", "count": {"$sum": 1}}}],
            "by_category": [{"$group": {"_id": "$category", "count": {"$sum": 1}}}],
            "by_zone": [{"$group": {"_id": "$location.zone_id", "count": {"$sum": 1}}}],
            "rating_dist": [
                {"$match": {"rating.stars": {"$ne": None}}},
                {"$group": {"_id": "$rating.stars", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}}
            ],
            "sla_data": [
                {"$match": {"status": {"$in": ["new", "triaged", "assigned", "in_progress"]}}},
                {"$project": {
                    "priority": 1,
                    "age_hours": {"$divide": [{"$subtract": [now, "$timestamps.created_at"]}, 3600000]},
                    "target": {"$ifNull": ["$sla_policy.target_hours", 72]},
                    "breach": {"$ifNull": ["$sla_policy.breach_threshold_hours", 120]}
                }},
                {"$group": {
                    "_id": None,
                    "at_risk": {"$sum": {"$cond": [{"$and": [{"$gte": ["$age_hours", "$target"]}, {"$lt": ["$age_hours", "$breach"]}]}, 1, 0]}},
                    "breached": {"$sum": {"$cond": [{"$gte": ["$age_hours", "$breach"]}, 1, 0]}},
                    "critical_breached": {"$sum": {"$cond": [{"$and": [{"$eq": ["$priority", "critical"]}, {"$gte": ["$age_hours", "$breach"]}]}, 1, 0]}}
                }}
            ]
        }}
    ]
    
    aggr_results = list(db.service_requests.aggregate(pipeline))[0]
    overall = aggr_results["overall"][0] if aggr_results["overall"] else {"total": 0, "open": 0, "resolved": 0, "avg_rating": 0}
    sla = aggr_results["sla_data"][0] if aggr_results["sla_data"] else {"at_risk": 0, "breached": 0, "critical_breached": 0}
    
    res = {
        "total_requests": overall["total"],
        "open_requests": overall["open"],
        "resolved_requests": overall["resolved"],
        "at_risk_count": sla["at_risk"],
        "breached_count": sla["breached"],
        "critical_breach_count": sla["critical_breached"],
        "sla_breach_percentage": round((sla["breached"] / overall["open"] * 100) if overall["open"] > 0 else 0, 1),
        "avg_rating": round(overall.get("avg_rating") or 0, 1),
        "by_status": {r["_id"]: r["count"] for r in aggr_results["by_status"]},
        "by_category": {r["_id"]: r["count"] for r in aggr_results["by_category"]},
        "by_zone": {r["_id"] or "Unknown": r["count"] for r in aggr_results["by_zone"]},
        "rating_distribution": {str(int(r["_id"])): r["count"] for r in aggr_results["rating_dist"]}
    }
    set_cache(cache_key, res)
    return res

@router.get("/stats")
async def get_basic_stats():
    """Basic aggregations for legacy dashboard compatibility"""
    pipeline = [
        {"$facet": {
            "by_status": [{"$group": {"_id": "$status", "count": {"$sum": 1}}}],
            "by_category": [{"$group": {"_id": "$category", "count": {"$sum": 1}}}]
        }}
    ]
    results = list(db.service_requests.aggregate(pipeline))[0]
    return {
        "by_status": {r["_id"]: r["count"] for r in results["by_status"]},
        "by_category": {r["_id"]: r["count"] for r in results["by_category"]}
    }

@router.get("/heatmap")
async def get_heatmap_feed(category: Optional[str] = None, priority: Optional[str] = None, include_closed: bool = False):
    """GeoJSON FeatureCollection with normalized weights and priority info"""
    # Note: cache disabled for debugging - can re-enable later
    # cache_key = f"heatmap_{category}_{priority}_{include_closed}"
    # cached = get_cached(cache_key)
    # if cached: return cached

    # By default, only show open requests. If include_closed is True, show all.
    if include_closed:
        query = {}  # No status filter - show all requests
        print(f"Heatmap query: ALL requests (include_closed={include_closed})")
    else:
        query = {"status": {"$in": ["new", "triaged", "assigned", "in_progress"]}}
        print(f"Heatmap query: OPEN requests only (include_closed={include_closed})")
    
    if category: 
        query["category"] = category
        print(f"  - Filtering by category: {category}")
    if priority: 
        query["priority"] = priority
        print(f"  - Filtering by priority: {priority}")
    
    requests = list(db.service_requests.find(query))
    print(f"  - Found {len(requests)} requests matching query")
    now = datetime.utcnow()
    features = []
    
    for req in requests:
        created = req["timestamps"].get("created_at", now)
        age_hours = (now - created).total_seconds() / 3600
        prio = req.get("priority", "medium")
        prio_weight = {"critical": 1.5, "high": 1.2, "medium": 0.8, "low": 0.5}.get(prio, 0.8)
        weight = prio_weight * (1 + min(age_hours / 168, 2.0))
        
        features.append({
            "type": "Feature",
            "properties": {
                "request_id": req["request_id"],
                "category": req["category"],
                "status": req["status"],
                "priority": prio,
                "weight": round(weight, 2),
                "age_hours": round(age_hours, 1)
            },
            "geometry": req["location"]
        })
    
    res = {"type": "FeatureCollection", "features": features}
    print(f\"  - Returning {len(features)} features in GeoJSON\")\n    # Cache disabled for debugging\n    # set_cache(cache_key, res)\n    return res

@router.get("/zones/geojson")
async def get_zone_summaries():
    """Return zones as GeoJSON with aggregated request counts for choropleth mapping"""
    # Fetch all defined zones
    zones = list(db.zones.find({}))
    
    # Aggregate requests by zone
    pipeline = [
        {"$match": {"status": {"$in": ["new", "triaged", "assigned", "in_progress"]}}},
        {"$group": {"_id": "$location.zone_id", "count": {"$sum": 1}}}
    ]
    zone_counts = {r["_id"]: r["count"] for r in db.service_requests.aggregate(pipeline)}
    
    features = []
    for zone in zones:
        zone_id = zone.get("zone_id")
        features.append({
            "type": "Feature",
            "properties": {
                "zone_id": zone_id,
                "name": zone.get("name"),
                "request_count": zone_counts.get(zone_id, 0),
                "density": "high" if zone_counts.get(zone_id, 0) > 10 else "medium" if zone_counts.get(zone_id, 0) > 3 else "low"
            },
            "geometry": zone.get("boundary")
        })
    
    return {"type": "FeatureCollection", "features": features}

@router.get("/cohorts")
async def get_cohorts():
    """Identifies recurring issues and hotspots"""
    pipeline = [
        {"$group": {
            "_id": "$location.address_hint",
            "count": {"$sum": 1},
            "categories": {"$addToSet": "$category"},
            "avg_rating": {"$avg": "$rating.stars"},
            "last_incident": {"$max": "$timestamps.created_at"}
        }},
        {"$match": {"count": {"$gt": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 15}
    ]
    return list(db.service_requests.aggregate(pipeline))

@router.get("/agents")
async def get_agent_analytics():
    """Fixed agent productivity with name lookup and ObjectId conversion"""
    # 1. Get all active agents
    agents = list(db.service_agents.find({"active": True}))
    agent_map = {str(a["_id"]): a["name"] for a in agents}
    
    # 2. Aggregate stats
    pipeline = [
        {"$match": {"assigned_agent_id": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": "$assigned_agent_id",
            "active_tasks": {"$sum": {"$cond": [{"$in": ["$status", ["assigned", "in_progress"]]}, 1, 0]}},
            "completed_tasks": {"$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}},
            "avg_resolution_hours": {"$avg": {
                "$cond": [
                    {"$and": [
                        {"$ne": [{"$type": "$timestamps.resolved_at"}, "missing"]},
                        {"$ne": [{"$type": "$timestamps.created_at"}, "missing"]}
                    ]},
                    {"$divide": [{"$subtract": ["$timestamps.resolved_at", "$timestamps.created_at"]}, 3600000]},
                    None
                ]
            }}
        }}
    ]
    stats = {r["_id"]: r for r in db.service_requests.aggregate(pipeline)}
    
    result = []
    for aid, name in agent_map.items():
        s = stats.get(aid, {"active_tasks": 0, "completed_tasks": 0, "avg_resolution_hours": 0})
        result.append({
            "agent_id": aid,
            "agent_name": name,
            "active_tasks": s["active_tasks"],
            "completed_tasks": s["completed_tasks"],
            "avg_resolution_hours": round(s["avg_resolution_hours"] or 0, 1),
            "score": round((s["completed_tasks"] / (s["active_tasks"] + 1)), 1)
        })
    
    return sorted(result, key=lambda x: x["completed_tasks"], reverse=True)

@router.get("/simulate-breach")
async def simulate_breach_rate():
    """Dev tool to artificially age requests to show non-zero breach rates"""
    # Target ANY open requests to ensure non-zero metrics
    db.service_requests.update_many(
        {"status": {"$in": ["new", "triaged", "assigned", "in_progress"]}},
        {"$set": {"timestamps.created_at": datetime.utcnow() - timedelta(days=15)}}
    )
    # Clear Cache to show results immediately
    CACHE.clear()
    return {"message": "Simulated breaches created for all open requests"}

@router.get("/export/csv")
async def export_analytics_csv(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    query = get_base_filters(start_date, end_date)
    requests = list(db.service_requests.find(query).sort("timestamps.created_at", -1))
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Request ID", "Category", "Status", "Priority", "Created At", "SLA State", "Rating"])
    
    for req in requests:
        ts = req.get("timestamps", {})
        sla_state = "Compliant"
        breach_hrs = req.get("sla_policy", {}).get("breach_threshold_hours", 120)
        
        created = ts.get("created_at")
        resolved = ts.get("resolved_at") or datetime.utcnow()
        
        if created:
            if (resolved - created).total_seconds() / 3600 > breach_hrs:
                sla_state = "Breached"
                
        rating_stars = ""
        if req.get("rating") and isinstance(req.get("rating"), dict):
            rating_stars = req.get("rating").get("stars", "")

        writer.writerow([
            req.get("request_id"),
            req.get("category"),
            req.get("status"),
            req.get("priority"),
            created.isoformat() if created else "",
            sla_state,
            rating_stars
        ])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cst_report_{datetime.now().strftime('%Y%m%d')}.csv"}
    )
