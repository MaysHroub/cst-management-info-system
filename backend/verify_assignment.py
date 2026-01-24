import requests
import datetime
import time

BASE_URL = "http://localhost:8000"

def create_agent(code, name, skills, shifts):
    print(f"Creating Agent {name}...")
    payload = {
        "agent_code": code,
        "name": name,
        "department": "Public Works",
        "skills": skills,
        "coverage": {
            "zone_ids": ["ZONE-A"],
            "geo_fence": {
                "type": "Polygon",
                "coordinates": [[[35.1, 31.8], [35.3, 31.8], [35.3, 32.0], [35.1, 32.0], [35.1, 31.8]]]
            }
        },
        "schedule": {"shifts": shifts}
    }
    try:
        res = requests.post(f"{BASE_URL}/agents/", json=payload)
        if res.status_code == 200:
            print("Success")
            return res.json()["_id"]
        else:
            # Maybe already exists, try to get by code (not implemented in API for search, but list works)
            print(f"Create failed (maybe exists): {res.text}")
            # simple lookup
            all_agents = requests.get(f"{BASE_URL}/agents/").json()
            for a in all_agents:
                if a["agent_code"] == code:
                    return a["_id"]
    except Exception as e:
        print(f"Error: {e}")
    return None

def verify_assignment():
    print("\nVerifying Assignment Logic...")
    
    # Current day/time
    now = datetime.datetime.utcnow()
    day_str = now.strftime("%a")
    print(f"Current Server Time (approx): {now} ({day_str})")
    
    # 1. Create Agents
    # Road Agent - On Shift
    road_id = create_agent("AG-ROAD-01", "Road Agent", ["road"], [{"day": day_str, "start": "00:00", "end": "23:59"}])
    # Water Agent - On Shift
    water_id = create_agent("AG-WATER-01", "Water Agent", ["water"], [{"day": day_str, "start": "00:00", "end": "23:59"}])
    
    # 2. Create Request (Category: pothole -> requires 'road')
    print("\nCreating Pothole Request...")
    req_payload = {
        "citizen_id": "anonymous",
        "anonymous": True,
        "category": "pothole",
        "description": "Auto-assign test",
        "priority": "high",
        "location": {"type": "Point", "coordinates": [35.2, 31.9]} # Inside coverage
    }
    req = requests.post(f"{BASE_URL}/requests/", json=req_payload).json()
    req_id = req["request_id"]
    print(f"Request Created: {req_id}")
    
    # 3. Triage (required for assignment)
    requests.patch(f"{BASE_URL}/requests/{req_id}/transition", json={"new_status": "triaged"})
    
    # 4. Auto Assign
    print("Triggering Auto-Assign...")
    assign_res = requests.post(f"{BASE_URL}/agents/assign-request/{req_id}")
    print(f"Assign Response: {assign_res.text}")
    
    if assign_res.status_code == 200:
        data = assign_res.json()
        print(f"Assigned To: {data['agent_name']} (ID: {data['agent_id']})")
        if data['agent_id'] == road_id:
            print("SUCCESS: Correctly assigned to Road Agent")
        else:
            print(f"FAILURE: Assigned to {data['agent_name']}, expected Road Agent")
    else:
        print("FAILURE: Assignment failed")

if __name__ == "__main__":
    verify_assignment()
