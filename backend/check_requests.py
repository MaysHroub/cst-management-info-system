#!/usr/bin/env python3
"""Quick script to check how many requests exist in the database"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from pymongo import MongoClient
    
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "cst_db")
    
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    
    # Test connection
    client.server_info()
    
    # Get all requests
    all_requests = list(db.service_requests.find({}))
    print(f"✓ Total requests in database: {len(all_requests)}")
    
    # Count by status
    open_statuses = ["new", "triaged", "assigned", "in_progress"]
    open_requests = [r for r in all_requests if r.get('status') in open_statuses]
    closed_requests = [r for r in all_requests if r.get('status') not in open_statuses]
    
    print(f"  - Open requests (new/triaged/assigned/in_progress): {len(open_requests)}")
    print(f"  - Closed/resolved requests: {len(closed_requests)}")
    
    # Show first few requests
    print("\nFirst 5 requests:")
    for req in all_requests[:5]:
        print(f"  - {req.get('request_id')}: status={req.get('status')}, priority={req.get('priority')}, has_location={bool(req.get('location'))}")
    
    if len(all_requests) == 0:
        print("\n⚠ No requests found in database! You may need to seed data first.")
        print("Try running: python3 seed_and_test.py")
    
except Exception as e:
    print(f"✗ Error connecting to database: {e}")
    print(f"\nMake sure:")
    print(f"  1. MongoDB is running (try: sudo systemctl status mongod)")
    print(f"  2. MONGO_URL is correct: {MONGO_URL}")
    print(f"  3. pymongo is installed (try: pip install pymongo)")
    sys.exit(1)
