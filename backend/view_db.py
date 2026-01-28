#!/usr/bin/env python3
"""Quick script to view MongoDB data"""
from app.database import get_database
from bson import json_util
import json

db = get_database()

print("=" * 60)
print("DATABASE: cst_db")
print("=" * 60)

# Collections overview
collections = db.list_collection_names()
print(f"\nCollections: {collections}")

# Count documents
print("\n--- Document Counts ---")
for coll in collections:
    count = db[coll].count_documents({})
    print(f"{coll}: {count} documents")

# Show sample requests
print("\n--- Sample Service Requests (First 3) ---")
requests = list(db.service_requests.find().limit(3))
for req in requests:
    print(json.dumps(req, indent=2, default=json_util.default))
    print("-" * 60)

# Show all zones
print("\n--- All Zones ---")
zones = list(db.zones.find())
for zone in zones:
    print(f"Zone ID: {zone.get('zone_id')}, Name: {zone.get('name')}")

# Show all agents
print("\n--- All Agents ---")
agents = list(db.service_agents.find())
for agent in agents:
    print(f"Agent: {agent.get('name')}, Zone: {agent.get('coverage', {}).get('zones', [])}")

print("\n" + "=" * 60)
