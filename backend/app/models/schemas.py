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
PyObjectId = Annotated[str, BeforeValidator(str)]

class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra='allow'  # Allow extra fields from MongoDB
    )

# --- Module 1: Service Requests ---

class Location(BaseModel):
    type: str = "Point"
    coordinates: List[float]
    address_hint: Optional[str] = None
    zone_id: Optional[str] = None

    model_config = ConfigDict(extra='allow')

class WorkflowState(BaseModel):
    current_state: RequestStatus = RequestStatus.NEW
    allowed_next: List[str] = ["triaged"]
    transition_rules_version: str = "v1.0"

    model_config = ConfigDict(extra='allow')

class SLAPolicy(BaseModel):
    policy_id: str = ""
    target_hours: int = 96
    breach_threshold_hours: int = 120

    model_config = ConfigDict(extra='allow')

class RequestEvidence(BaseModel):
    type: str = "photo"
    url: str
    uploaded_at: Optional[datetime] = None

    model_config = ConfigDict(extra='allow')

class Comment(BaseModel):
    id: str
    text: str
    author_id: str
    author_type: str = "citizen"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(extra='allow')

class Rating(BaseModel):
    stars: int
    comment: Optional[str] = None
    reason_codes: List[str] = []
    dispute: bool = False
    dispute_reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(extra='allow')

class Milestone(BaseModel):
    type: str
    timestamp: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra='allow')

class ServiceRequestCreate(BaseModel):
    citizen_id: str
    anonymous: bool = False
    category: str
    sub_category: Optional[str] = None
    description: str
    priority: Priority = Priority.MEDIUM
    location: Location
    evidence: List[RequestEvidence] = []

class ServiceRequest(MongoBaseModel):
    request_id: Optional[str] = None
    citizen_id: Optional[str] = None
    anonymous: bool = False
    category: Optional[str] = None
    sub_category: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    location: Optional[Location] = None
    workflow: Optional[WorkflowState] = None
    sla_policy: Optional[SLAPolicy] = None
    timestamps: Optional[Dict[str, Any]] = None
    assigned_agent_id: Optional[str] = None
    evidence: List[RequestEvidence] = []
    comments: List[Comment] = []
    rating: Optional[Rating] = None
    milestones: List[Milestone] = []

# --- Module 2: Citizens ---

class NotificationPreferences(BaseModel):
    on_status_change: bool = True
    on_resolution: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False

    model_config = ConfigDict(extra='allow')

class PrivacySettings(BaseModel):
    default_anonymous: bool = False
    share_publicly_on_map: bool = True

    model_config = ConfigDict(extra='allow')

class ContactPreferences(BaseModel):
    preferred_contact: str = "email"
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    model_config = ConfigDict(extra='allow')

class CitizenPreferences(BaseModel):
    notifications: NotificationPreferences = NotificationPreferences()
    privacy: PrivacySettings = PrivacySettings()
    language: str = "en"

    model_config = ConfigDict(extra='allow')

class CitizenCreate(BaseModel):
    full_name: str
    password: str
    contacts: ContactPreferences
    address_zone_id: Optional[str] = None
    preferences: Optional[CitizenPreferences] = None

class Citizen(MongoBaseModel):
    full_name: Optional[str] = None
    verification_state: Optional[str] = None
    contacts: Optional[ContactPreferences] = None
    preferences: Optional[CitizenPreferences] = None
    stats: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None

# --- Module 3: Service Agents ---

class AgentSchedule(BaseModel):
    shifts: List[Dict[str, str]] = []
    timezone: str = "Asia/Jerusalem"
    on_call: bool = False

    model_config = ConfigDict(extra='allow')

class GeoFence(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]]

    model_config = ConfigDict(extra='allow')

class AgentCoverage(BaseModel):
    zone_ids: List[str]
    geo_fence: Optional[GeoFence] = None

    model_config = ConfigDict(extra='allow')

class AgentCreate(BaseModel):
    agent_code: str
    name: str
    department: str
    skills: List[str]
    coverage: AgentCoverage
    schedule: AgentSchedule

class Agent(MongoBaseModel):
    agent_code: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None
    skills: List[str] = []
    coverage: Optional[AgentCoverage] = None
    schedule: Optional[AgentSchedule] = None
    active: bool = True
    created_at: Optional[datetime] = None
    current_workload: int = 0
# --- Module 5: Zones ---

class ZoneCreate(BaseModel):
    zone_id: str
    name: str
    boundary: GeoFence # Reuse GeoFence (Polygon)
    meta: Optional[Dict[str, Any]] = {}

class Zone(MongoBaseModel):
    zone_id: str
    name: str
    boundary: GeoFence
    meta: Optional[Dict[str, Any]] = {}
    created_at: Optional[datetime] = None
