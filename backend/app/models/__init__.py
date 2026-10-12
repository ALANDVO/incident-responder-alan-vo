from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import (
    String, Text, DateTime, ForeignKey, Enum as SQLEnum, Integer, Index, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class SeverityLevel(str, PyEnum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


class IncidentStatus(str, PyEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CommsChannel(str, PyEnum):
    STATUS = "status"
    SLACK = "slack"
    EMAIL = "email"


class CommsPhase(str, PyEnum):
    INITIAL = "initial"
    UPDATE = "update"
    EXEC = "exec"
    RESOLVED = "resolved"
    CUSTOMER = "customer"
    LEADERSHIP = "leadership"
    ENGINEERING = "engineering"


class UserRole(str, PyEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    raw_data: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(
        SQLEnum(IncidentStatus), default=IncidentStatus.OPEN, nullable=False
    )
    severity: Mapped[Optional[SeverityLevel]] = mapped_column(SQLEnum(SeverityLevel), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    triage_results: Mapped[List["TriageResult"]] = relationship(
        "TriageResult", back_populates="incident", cascade="all, delete-orphan"
    )
    blast_analyses: Mapped[List["BlastAnalysis"]] = relationship(
        "BlastAnalysis", back_populates="incident", cascade="all, delete-orphan"
    )
    comms_templates: Mapped[List["CommsTemplate"]] = relationship(
        "CommsTemplate", back_populates="incident", cascade="all, delete-orphan"
    )
    postmortems: Mapped[List["Postmortem"]] = relationship(
        "Postmortem", back_populates="incident", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_incidents_status_created", "status", "created_at"),
        Index("ix_incidents_severity", "severity"),
    )


class TriageResult(Base):
    __tablename__ = "triage_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    severity: Mapped[SeverityLevel] = mapped_column(SQLEnum(SeverityLevel), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    containment_plan: Mapped[str] = mapped_column(Text, nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="triage_results")


class BlastAnalysis(Base):
    __tablename__ = "blast_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    affected_services: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    data_impact: Mapped[str] = mapped_column(Text, nullable=False)
    dependency_chain: Mapped[str] = mapped_column(Text, nullable=False)
    user_impact: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_estimate: Mapped[str] = mapped_column(Text, nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="blast_analyses")


class CommsTemplate(Base):
    __tablename__ = "comms_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    channel: Mapped[CommsChannel] = mapped_column(SQLEnum(CommsChannel), nullable=False)
    phase: Mapped[CommsPhase] = mapped_column(SQLEnum(CommsPhase), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="comms_templates")

    __table_args__ = (
        Index("ix_comms_incident_channel_phase", "incident_id", "channel", "phase"),
    )


class Postmortem(Base):
    __tablename__ = "postmortems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    timeline: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    what_went_well: Mapped[str] = mapped_column(Text, nullable=False)
    what_went_poorly: Mapped[str] = mapped_column(Text, nullable=False)
    contributing_factors: Mapped[str] = mapped_column(Text, nullable=False)
    action_items: Mapped[List[dict]] = mapped_column(JSON, nullable=False, default=list)
    lessons_learned: Mapped[str] = mapped_column(Text, nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="postmortems")