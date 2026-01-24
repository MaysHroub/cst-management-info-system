from pydantic import BaseModel, Field, EmailStr, BeforeValidator, ConfigDict
from typing import List, Optional, Any, Dict, Annotated
from datetime import datetime
from enum import Enum
from bson import ObjectId

# --- Enums ---
class RequestStatus(str, Enum):
    NEW = "new"
    TRIAGED = "triaged"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CitizenVerificationState(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"

# --- Shared ---
# Represents an ObjectId field in the database.
# It will be represented as a str on the model so that Pydantic can serialize it to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]

class MongoBaseModel(BaseModel):
    # The _id field will be mapped to the id field in the model.
    id: Optional[PyObjectId] = Field(alias="_id", default=None)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

# --- Module 1: Service Requests ---

class Location(BaseModel):
    type: str = "Point"
    coordinates: List[float] # [long, lat]
    address_hint: Optional[str] = None
    zone_id: Optional[str] = None

class WorkflowState(BaseModel):
    current_state: RequestStatus = RequestStatus.NEW
    allowed_next: List[RequestStatus] = [RequestStatus.TRIAGED]
    transition_rules_version: str = "v1.0"

class SLAPolicy(BaseModel):
    policy_id: str
    target_hours: int
    breach_threshold_hours: int

class RequestEvidence(BaseModel):
    type: str = "photo"
    url: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

class ServiceRequestCreate(BaseModel):
    citizen_id: str
    anonymous: bool = False
    category: str
    sub_category: Optional[str] = None
    description: str
    priority: Priority = Priority.MEDIUM
    location: Location
    evidence: List[RequestEvidence] = []

class ServiceRequest(MongoBaseModel, ServiceRequestCreate):
    request_id: str
    status: RequestStatus = RequestStatus.NEW
    workflow: WorkflowState
    timestamps: Dict[str, Optional[datetime]] = {
        "created_at": None,
        "triaged_at": None,
        "assigned_at": None,
        "resolved_at": None,
        "closed_at": None,
        "updated_at": None
    }
    assigned_agent_id: Optional[str] = None

# --- Module 2: Citizens ---

class ContactPreferences(BaseModel):
    preferred_contact: str = "email"
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class CitizenCreate(BaseModel):
    full_name: str
    password: str  # In real app, hash this
    contacts: ContactPreferences
    address_zone_id: Optional[str] = None

class Citizen(MongoBaseModel):
    full_name: str
    verification_state: CitizenVerificationState = CitizenVerificationState.UNVERIFIED
    contacts: ContactPreferences
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- Module 3: Service Agents ---

class AgentSchedule(BaseModel):
    shifts: List[Dict[str, str]] = [] # e.g., [{"day": "Mon", "start": "08:00", "end": "16:00"}]

class GeoFence(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]]

class AgentCoverage(BaseModel):
    zone_ids: List[str]
    geo_fence: Optional[GeoFence] = None

class AgentCreate(BaseModel):
    agent_code: str
    name: str
    department: str
    skills: List[str]
    coverage: AgentCoverage
    schedule: AgentSchedule

class Agent(MongoBaseModel, AgentCreate):
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
