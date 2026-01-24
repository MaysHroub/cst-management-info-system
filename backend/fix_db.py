from app.database import get_database

db = get_database()

print("Current Indexes on service_agents:")
for name in db.service_agents.index_information():
    print(f"- {name}")

print("\nDropping 'agent_id_1' if exists...")
try:
    db.service_agents.drop_index("agent_id_1")
    print("Dropped successfully.")
except Exception as e:
    print(f"Failed to drop or not found: {e}")

print("\nVerifying indexes again:")
for name in db.service_agents.index_information():
    print(f"- {name}")
