import os
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "cst_db")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

def get_database():
    return db

def setup_indexes():
    try:
        # Service Requests Indexes
        db.service_requests.create_index([("location", "2dsphere")])
        db.service_requests.create_index("request_id", unique=True)
        db.service_requests.create_index("status")
        db.service_requests.create_index("category")
        db.service_requests.create_index("citizen_ref.citizen_id")
        
        # Citizens Indexes
        db.citizens.create_index("contacts.email", unique=True)
        db.citizens.create_index("contacts.phone")
        
        # Service Agents Indexes
        db.service_agents.create_index("agent_code", unique=True)
        db.service_agents.create_index([("coverage.geo_fence", "2dsphere")])
        print("Indexes created successfully.")
    except Exception as e:
        print(f"Index creation warning: {e}")
