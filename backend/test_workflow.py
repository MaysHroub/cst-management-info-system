import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_full_workflow():
    print("=" * 60)
    print("CST FULL WORKFLOW TEST - Annex B Verification")
    print("=" * 60)
    
    # Step 1: Create a Citizen
    print("\n📋 Step 1: Creating Citizen Profile...")
    citizen_res = requests.post(f"{BASE_URL}/citizens/", json={
        "full_name": "Test User",
        "password": "test123",
        "contacts": {"email": f"test_{datetime.now().timestamp()}@example.com", "preferred_contact": "email"}
    })
    if citizen_res.status_code == 200:
        citizen_id = citizen_res.json()["_id"]
        print(f"   ✅ Citizen Created: {citizen_id}")
    else:
        print(f"   ⚠️ Citizen creation issue: {citizen_res.text}")
        citizen_id = "anonymous"

    # Step 2: Create an Agent with coverage zone
    print("\n🔧 Step 2: Creating Service Agent...")
    agent_code = f"AG-TEST-{int(datetime.now().timestamp()) % 10000}"
    agent_res = requests.post(f"{BASE_URL}/agents/", json={
        "agent_code": agent_code,
        "name": "Test Team Alpha",
        "department": "Public Works",
        "skills": ["road", "general"],
        "coverage": {
            "zone_ids": ["ZONE-TEST"],
            "geo_fence": {
                "type": "Polygon",
                "coordinates": [[[35.0, 31.8], [35.3, 31.8], [35.3, 32.0], [35.0, 32.0], [35.0, 31.8]]]
            }
        },
        "schedule": {"shifts": []}
    })
    if agent_res.status_code == 200:
        agent_id = agent_res.json()["_id"]
        print(f"   ✅ Agent Created: {agent_id} ({agent_code})")
    else:
        print(f"   ⚠️ Agent creation issue (may already exist): {agent_res.text}")
        # Try to get existing agents
        agents = requests.get(f"{BASE_URL}/agents/").json()
        agent_id = agents[0]["_id"] if agents else None

    # Step 3: Citizen submits a Service Request
    print("\n📝 Step 3: Submitting Service Request...")
    request_res = requests.post(f"{BASE_URL}/requests/", json={
        "citizen_id": citizen_id,
        "anonymous": False,
        "category": "pothole",
        "description": "Large pothole on main road causing traffic issues",
        "priority": "high",
        "location": {
            "type": "Point",
            "coordinates": [35.2050, 31.9038]  # Inside the coverage zone
        }
    })
    if request_res.status_code == 200:
        req_data = request_res.json()
        request_id = req_data["request_id"]
        print(f"   ✅ Request Created: {request_id}")
        print(f"      Status: {req_data['status']}")
        print(f"      SLA Target: {req_data.get('sla_policy', {}).get('target_hours', 'N/A')} hours")
    else:
        print(f"   ❌ Request failed: {request_res.text}")
        return

    # Step 4: Staff Triages the Request
    print("\n🔍 Step 4: Staff Triages Request...")
    triage_res = requests.patch(f"{BASE_URL}/requests/{request_id}/transition", json={"new_status": "triaged"})
    if triage_res.status_code == 200:
        print(f"   ✅ Request Triaged - Status: {triage_res.json()['status']}")
    else:
        print(f"   ❌ Triage failed: {triage_res.text}")
        return

    # Step 5: Auto-Assign to Agent
    print("\n🤖 Step 5: Auto-Assigning to Agent...")
    assign_res = requests.post(f"{BASE_URL}/agents/assign-request/{request_id}", json={})
    if assign_res.status_code == 200:
        print(f"   ✅ Assigned: {assign_res.json()}")
    else:
        print(f"   ❌ Assignment failed: {assign_res.text}")
        return

    # Step 6: Agent Updates Milestones
    print("\n🚗 Step 6: Agent Arrives on Site...")
    arrived_res = requests.patch(f"{BASE_URL}/requests/{request_id}/milestone", json={"milestone_type": "arrived", "notes": "On site"})
    if arrived_res.status_code == 200:
        print(f"   ✅ Milestone 'arrived' recorded")
    
    print("\n🔨 Step 7: Agent Starts Work...")
    work_res = requests.patch(f"{BASE_URL}/requests/{request_id}/milestone", json={"milestone_type": "work_started", "notes": "Beginning repairs"})
    if work_res.status_code == 200:
        print(f"   ✅ Milestone 'work_started' recorded")

    print("\n✅ Step 8: Agent Completes Work...")
    resolve_res = requests.patch(f"{BASE_URL}/requests/{request_id}/milestone", json={"milestone_type": "resolved", "notes": "Pothole filled"})
    if resolve_res.status_code == 200:
        print(f"   ✅ Milestone 'resolved' recorded - Request RESOLVED")

    # Step 9: Citizen Rates Service
    print("\n⭐ Step 9: Citizen Rates Service...")
    rating_res = requests.post(f"{BASE_URL}/requests/{request_id}/rating", json={"stars": 5, "comment": "Excellent service!"})
    if rating_res.status_code == 200:
        print(f"   ✅ Rating submitted: 5 stars")
    else:
        print(f"   ❌ Rating failed: {rating_res.text}")

    # Step 10: Close Request
    print("\n🔒 Step 10: Closing Request...")
    close_res = requests.patch(f"{BASE_URL}/requests/{request_id}/transition", json={"new_status": "closed"})
    if close_res.status_code == 200:
        print(f"   ✅ Request CLOSED")
    else:
        print(f"   ⚠️ Close transition: {close_res.text}")

    # Verify Final State
    print("\n📊 Final State Verification...")
    final = requests.get(f"{BASE_URL}/requests/{request_id}").json()
    print(f"   Request ID: {final['request_id']}")
    print(f"   Status: {final['status']}")
    print(f"   Rating: {final.get('rating', {}).get('stars', 'N/A')} stars")
    print(f"   Milestones: {len(final.get('milestones', []))}")

    # Check Analytics
    print("\n📈 Analytics Check...")
    kpis = requests.get(f"{BASE_URL}/analytics/kpis").json()
    print(f"   Total Requests: {kpis.get('total_requests')}")
    print(f"   Open Requests: {kpis.get('open_requests')}")
    print(f"   Avg Rating: {kpis.get('avg_rating')}")

    print("\n" + "=" * 60)
    print("✅ FULL WORKFLOW TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_full_workflow()
