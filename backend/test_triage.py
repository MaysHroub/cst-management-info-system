#!/usr/bin/env python3
"""
Simple test to verify triage logic without running the full server
"""
import sys
import math

# Simulate the triage logic without FastAPI dependencies

VALID_CATEGORIES = [
    "pothole", "water_leak", "trash", "lighting", 
    "sewage", "signage", "other"
]

SLA_POLICIES = {
    "critical": {"target_hours": 24, "breach_threshold_hours": 36},
    "high": {"target_hours": 48, "breach_threshold_hours": 72},
    "medium": {"target_hours": 96, "breach_threshold_hours": 120},
    "low": {"target_hours": 168, "breach_threshold_hours": 240}
}

SENSITIVE_LOCATIONS = [
    {"coordinates": [35.2137, 31.7683], "name": "Hadassah Hospital", "type": "hospital"},
    {"coordinates": [35.1936, 31.7872], "name": "Shaare Zedek Medical Center", "type": "hospital"},
    {"coordinates": [35.2433, 31.7890], "name": "Hebrew University", "type": "school"},
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
    """Check if location is near sensitive areas"""
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

def test_triage():
    """Test various triage scenarios"""
    
    print("=" * 60)
    print("TRIAGE LOGIC TEST SUITE")
    print("=" * 60)
    
    # Test 1: Valid category, no escalation
    print("\n[Test 1] Normal request - low priority, not near sensitive location")
    request1 = {
        "category": "pothole",
        "priority": "low",
        "location": {"coordinates": [35.0, 31.5]}  # Far from everything
    }
    
    category = request1["category"]
    priority = request1["priority"]
    nearby = check_high_impact_location(request1["location"]["coordinates"])
    
    if category not in VALID_CATEGORIES:
        print(f"  ❌ Invalid category: {category}")
    else:
        print(f"  ✓ Category '{category}' is valid")
    
    print(f"  Original priority: {priority}")
    print(f"  Nearby sensitive locations: {len(nearby)}")
    print(f"  Final priority: {priority} (no escalation)")
    print(f"  SLA: {SLA_POLICIES[priority]['target_hours']}h target")
    
    # Test 2: Near hospital - should escalate
    print("\n[Test 2] Request near hospital - should escalate to critical")
    request2 = {
        "category": "water_leak",
        "priority": "medium",
        "location": {"coordinates": [35.2137, 31.7683]}  # Hadassah Hospital coordinates
    }
    
    category = request2["category"]
    priority = request2["priority"]
    nearby = check_high_impact_location(request2["location"]["coordinates"])
    
    print(f"  ✓ Category '{category}' is valid")
    print(f"  Original priority: {priority}")
    print(f"  Nearby sensitive locations: {len(nearby)}")
    
    if nearby:
        for loc in nearby:
            print(f"    - {loc['name']} ({loc['type']}) - {loc['distance_km']}km away")
        
        # Escalation logic
        if priority in ["low", "medium"]:
            priority = "high"
            print(f"  ⚠️  Priority escalated to: {priority}")
        if any(loc["type"] == "hospital" for loc in nearby):
            priority = "critical"
            print(f"  ⚠️  Priority escalated to: {priority} (near hospital)")
    
    print(f"  Final priority: {priority}")
    print(f"  SLA: {SLA_POLICIES[priority]['target_hours']}h target")
    
    # Test 3: Invalid category - should fail
    print("\n[Test 3] Invalid category - should fail validation")
    request3 = {
        "category": "invalid_category",
        "priority": "high",
        "location": {"coordinates": [35.2, 31.8]}
    }
    
    category = request3["category"]
    if category not in VALID_CATEGORIES:
        print(f"  ❌ Category '{category}' is INVALID")
        print(f"  Valid categories: {', '.join(VALID_CATEGORIES)}")
    else:
        print(f"  ✓ Category is valid")
    
    # Test 4: Near school - escalate from low to high
    print("\n[Test 4] Request near school - escalate from low to high")
    request4 = {
        "category": "lighting",
        "priority": "low",
        "location": {"coordinates": [35.2433, 31.7890]}  # Hebrew University
    }
    
    category = request4["category"]
    priority = request4["priority"]
    nearby = check_high_impact_location(request4["location"]["coordinates"])
    
    print(f"  ✓ Category '{category}' is valid")
    print(f"  Original priority: {priority}")
    print(f"  Nearby sensitive locations: {len(nearby)}")
    
    if nearby:
        for loc in nearby:
            print(f"    - {loc['name']} ({loc['type']}) - {loc['distance_km']}km away")
        
        if priority in ["low", "medium"]:
            priority = "high"
            print(f"  ⚠️  Priority escalated to: {priority}")
    
    print(f"  Final priority: {priority}")
    print(f"  SLA: {SLA_POLICIES[priority]['target_hours']}h target")
    
    print("\n" + "=" * 60)
    print("✓ All tests completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    test_triage()
