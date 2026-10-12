from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class SeverityLevel(str, Enum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


class IncidentStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CommsChannel(str, Enum):
    STATUS = "status"
    SLACK = "slack"
    EMAIL = "email"


class CommsPhase(str, Enum):
    INITIAL = "initial"
    UPDATE = "update"
    EXEC = "exec"
    RESOLVED = "resolved"
    CUSTOMER = "customer"
    LEADERSHIP = "leadership"
    ENGINEERING = "engineering"


class UserRole(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class UserCreate(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: UserRole = UserRole.VIEWER


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    email: str
    roles: List[str]


class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    raw_data: Optional[str] = None


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[IncidentStatus] = None
    severity: Optional[SeverityLevel] = None


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    raw_data: Optional[str]
    status: IncidentStatus
    severity: Optional[SeverityLevel]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]


class IncidentListResponse(BaseModel):
    items: List[IncidentRead]
    total: int
    page: int
    page_size: int


class TriageRequest(BaseModel):
    incident_id: int
    use_llm: bool = True


class TriageResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    severity: SeverityLevel
    confidence: float
    reasoning: str
    containment_plan: str
    llm_provider: str
    llm_model: str
    created_at: datetime


class BlastAnalysisRequest(BaseModel):
    incident_id: int
    services: Optional[List[str]] = None
    use_llm: bool = True


class BlastAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    affected_services: List[str]
    data_impact: str
    dependency_chain: str
    user_impact: str
    recovery_estimate: str
    llm_provider: str
    llm_model: str
    created_at: datetime


class CommsTemplateRequest(BaseModel):
    incident_id: int
    channel: CommsChannel
    phase: CommsPhase
    use_llm: bool = True


class CommsTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    channel: CommsChannel
    phase: CommsPhase
    content: str
    llm_provider: str
    llm_model: str
    created_at: datetime


class PostmortemRequest(BaseModel):
    incident_id: int
    use_llm: bool = True


class PostmortemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    summary: str
    timeline: str
    root_cause: str
    what_went_well: str
    what_went_poorly: str
    contributing_factors: str
    action_items: List[Dict[str, Any]]
    lessons_learned: str
    llm_provider: str
    llm_model: str
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


class LLMProvidersResponse(BaseModel):
    providers: List[str]
    current: str
    model: str