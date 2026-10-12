from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, UserRole
from app.services.incident import IncidentService
from app.services.llm import LLMClient, get_llm_client
from app.api.auth import require_roles
from app.schemas import (
    IncidentCreate,
    IncidentUpdate,
    IncidentRead,
    IncidentListResponse,
    TriageRequest,
    TriageResultRead,
    BlastAnalysisRequest,
    BlastAnalysisRead,
    CommsTemplateRequest,
    CommsTemplateRead,
    PostmortemRequest,
    PostmortemRead,
    SeverityLevel,
    IncidentStatus,
)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

# Auth policy: every data endpoint requires authentication. Readers may be
# viewers; writers must be operators or admins.
require_viewer = require_roles(UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN)
require_operator = require_roles(UserRole.OPERATOR, UserRole.ADMIN)


def get_incident_service(
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
) -> IncidentService:
    return IncidentService(db, llm)


@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_operator)],
)
async def create_incident(
    data: IncidentCreate,
    service: IncidentService = Depends(get_incident_service),
):
    incident = await service.create_incident(data)
    return incident


@router.get("", response_model=IncidentListResponse, dependencies=[Depends(require_viewer)])
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[IncidentStatus] = None,
    severity: Optional[SeverityLevel] = None,
    service: IncidentService = Depends(get_incident_service),
):
    incidents, total = await service.list_incidents(page, page_size, status, severity)
    return IncidentListResponse(
        items=incidents,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{incident_id}", response_model=IncidentRead, dependencies=[Depends(require_viewer)])
async def get_incident(
    incident_id: int,
    service: IncidentService = Depends(get_incident_service),
):
    incident = await service.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.patch("/{incident_id}", response_model=IncidentRead, dependencies=[Depends(require_operator)])
async def update_incident(
    incident_id: int,
    data: IncidentUpdate,
    service: IncidentService = Depends(get_incident_service),
):
    incident = await service.update_incident(incident_id, data)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_operator)])
async def delete_incident(
    incident_id: int,
    service: IncidentService = Depends(get_incident_service),
):
    success = await service.delete_incident(incident_id)
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found")


@router.post("/{incident_id}/triage", response_model=TriageResultRead, dependencies=[Depends(require_operator)])
async def triage_incident(
    incident_id: int,
    request: TriageRequest,
    service: IncidentService = Depends(get_incident_service),
):
    if request.incident_id != incident_id:
        raise HTTPException(status_code=400, detail="Incident ID mismatch")
    result = await service.triage_incident(request)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@router.post("/{incident_id}/blast", response_model=BlastAnalysisRead, dependencies=[Depends(require_operator)])
async def analyze_blast_radius(
    incident_id: int,
    request: BlastAnalysisRequest,
    service: IncidentService = Depends(get_incident_service),
):
    if request.incident_id != incident_id:
        raise HTTPException(status_code=400, detail="Incident ID mismatch")
    result = await service.analyze_blast_radius(request)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@router.post("/{incident_id}/comms", response_model=CommsTemplateRead, dependencies=[Depends(require_operator)])
async def generate_comms(
    incident_id: int,
    request: CommsTemplateRequest,
    service: IncidentService = Depends(get_incident_service),
):
    if request.incident_id != incident_id:
        raise HTTPException(status_code=400, detail="Incident ID mismatch")
    result = await service.generate_comms(request)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@router.post("/{incident_id}/postmortem", response_model=PostmortemRead, dependencies=[Depends(require_operator)])
async def generate_postmortem(
    incident_id: int,
    request: PostmortemRequest,
    service: IncidentService = Depends(get_incident_service),
):
    if request.incident_id != incident_id:
        raise HTTPException(status_code=400, detail="Incident ID mismatch")
    result = await service.generate_postmortem(request)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result