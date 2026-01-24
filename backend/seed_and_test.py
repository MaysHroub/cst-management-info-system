import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def run_test():
    print("--- 1. Creating Agent (Downtown Team) ---")
    agent_payload = {
        "agent_code": "AG-DT-01",
        "name": "Downtown Team A",
        "department": "Public Works",
        "skills": ["road", "general"],
        "coverage": {
            "zone_ids": ["ZONE-DT"],
            "geo_fence": {
                "type": "Polygon",
                "coordinates": [[
                    [35.19, 31.89],
                    [35.22, 31.89],
                    [35.22, 31.92],
                    [35.19, 31.92],
                    [35.19, 31.89]
                ]]
            }
        },
        "schedule": {"shifts": []}
    }
    # Clean up first (optional/risky in prod but ok here)
    # response = requests.delete(f"{BASE_URL}/agents/AG-DT-01") 
    
    try:
        res = requests.post(f"{BASE_URL}/agents/", json=agent_payload)
        if res.status_code == 200:
            print("Agent Created:", res.json()["_id"])
        else:
            print("Agent Creation Failed (might exist):", res.text)
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- 2. Creating Citizen ---")
    citizen_payload = {
        "full_name": "John Doe",
        "password": "secret",
        "contacts": {"email": "john@example.com"}
    }
    
    res = requests.post(f"{BASE_URL}/citizens/", json=citizen_payload)
    if res.status_code == 200:
        citizen_id = res.json()["_id"]
        print("Citizen Created:", citizen_id)
    elif res.status_code == 400:
         print("Citizen exists, fetching...")
         # fetch logic skipped, we assume we can proceed
         citizen_id = "675000000000000000000101" # Stub
    else:
        print("Citizen Failed:", res.text)
        citizen_id = "stub_id"

    print("\n--- 3. Creating Service Request (Inside Agent Zone) ---")
    req_payload = {
        "citizen_id": citizen_id,
        "category": "pothole",
        "description": "Big hole",
        "priority": "high",
        "location": {
            "type": "Point",
            "coordinates": [35.2050, 31.9038] # Inside 31.89-31.92 / 35.19-35.22
        }
    }
    
    res = requests.post(f"{BASE_URL}/requests/", json=req_payload)
    if res.status_code == 200:
        req_data = res.json()
        req_id = req_data["request_id"]
        print(f"Request Created: {req_id} (Status: {req_data['status']})")
    else:
        print("Request Failed:", res.text)
        return

    print("\n--- 4. Triage Request (Transition Status) ---")
    res = requests.patch(f"{BASE_URL}/requests/{req_id}/transition", json={"new_status": "triaged"})
    if res.status_code == 200:
        print("Request Triaged")
    else:
        print("Triage Failed:", res.text)

    print("\n--- 5. Auto-Assign Request ---")
    res = requests.post(f"{BASE_URL}/agents/assign-request/{req_id}")
    if res.status_code == 200:
        print("Assignment Success:", res.json())
    else:
        print("Assignment Failed:", res.text)

if __name__ == "__main__":
    run_test()
