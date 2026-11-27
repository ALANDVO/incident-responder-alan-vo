from typing import Optional, Literal

from fastapi import APIRouter, Request, HTTPException

from app.core.database import get_db
from app.services.classifier import classify_incident, generate_containment_plan
from app.services.incident import IncidentService
from app.schemas import IncidentCreate


router = APIRouter(prefix="/api/webhook", tags=["webhook"])


async def _parse_pagerduty_payload(payload: dict) -> Optional[dict]:
    """Extract incident fields from a PagerDuty webhook payload.

    Handles v2 webhook format. Returns a dict with:
    - title, description, severity, source, event_type
    """
    event_type = payload.get("event_type", "")
    payload_data = payload.get("payload", payload)

    # v2 webhook format
    if event_type == "pd.event.problem.created" or event_type == "pd.event.problem.acknowledged":
        severity_map = {
            "critical": "SEV1",
            "high": "SEV2",
            "warning": "SEV3",
            "low": "SEV4",
        }
        severity = severity_map.get(payload_data.get("severity", "low"), "SEV3")
        title = payload_data.get("title", "PagerDuty Alert")
        # Build description from incident details
        incident = payload_data.get("incident", {})
        description_parts = []
        if incident.get("url"):
            description_parts.append(f"[PagerDuty Incident]({incident['url']})")
        if incident.get("status"):
            description_parts.append(f"Status: {incident['status']}")
        if incident.get("priority", {}).get("id"):
            description_parts.append(f"Priority: {incident['priority']['summary']}")
        description = " | ".join(description_parts) if description_parts else "PagerDuty alert received"
        source = payload_data.get("routing_rule", {}).get("name", "PagerDuty")
        return {
            "title": title,
            "description": description,
            "severity": severity,
            "source": source,
            "event_type": event_type,
            "raw_data": str(payload),
        }

    # OpsGenie webhook format
    if payload.get("alert"):
        alert = payload["alert"]
        severity_map = {
            "P1": "SEV1",
            "P2": "SEV2",
            "P3": "SEV3",
            "P4": "SEV4",
        }
        severity = severity_map.get(alert.get("priority", "P4"), "SEV3")
        title = alert.get("name", "OpsGenie Alert")
        description = alert.get("message", "OpsGenie alert received")
        source = alert.get("source", "OpsGenie")
        return {
            "title": title,
            "description": description,
            "severity": severity,
            "source": source,
            "event_type": "opsgenie.alert",
            "raw_data": str(payload),
        }

    return None


async def _parse_opsgenie_payload(payload: dict) -> Optional[dict]:
    """Extract incident fields from an OpsGenie webhook payload.

    Handles OpsGenie alert payloads. Returns normalized dict or None.
    """
    if not payload.get("alert"):
        return None

    alert = payload["alert"]
    severity_map = {
        "P1": "SEV1",
        "P2": "SEV2",
        "P3": "SEV3",
        "P4": "SEV4",
    }
    severity = severity_map.get(alert.get("priority", "P4"), "SEV3")
    title = alert.get("name", "OpsGenie Alert")
    description = alert.get("message", "OpsGenie alert received")
    source = alert.get("source", "OpsGenie")
    return {
        "title": title,
        "description": description,
        "severity": severity,
        "source": source,
        "event_type": "opsgenie.alert",
        "raw_data": str(payload),
    }


@router.post("/pagerduty", tags=["webhook"])
async def pagerduty_webhook(
    request: Request,
) -> dict:
    """Receive and parse PagerDuty webhook events.

    Creates an incident in the timeline from the webhook payload.
    For SEV1/SEV2 alarms, automatically triggers deterministic SEV classification.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    parsed = await _parse_pagerduty_payload(payload)
    if not parsed:
        raise HTTPException(status_code=400, detail="Unrecognized PagerDuty event type")

    db_gen = get_db()
    db = await anext(db_gen)

    service = IncidentService(db)

    # Create incident from webhook data
    incident_create = IncidentCreate(
        title=parsed["title"],
        description=parsed["description"],
        raw_data=parsed["raw_data"],
        status="open",
    )

    created = await service.create_incident(incident_create)

    # Auto-trigger SEV classification for high-urgency alarms (SEV1/SEV2)
    if parsed["severity"] in ("SEV1", "SEV2"):
        try:
            classification = classify_incident(parsed["description"])

            # Create triage result from classification
            triage_result = await service.triage_incident(
                incident_id=created.id,
                use_llm=False,  # use deterministic classification
            )

            # Override with deterministic classification result
            from app.models import TriageResult, SeverityLevel

            # Map classifier confidence to a reasonable value
            confidence = 0.95 if classification.indicators else 0.7
            reasoning = f"Auto-classified from PagerDuty webhook ({len(classification.indicators)} indicators matched)"

            # Insert triage directly
            from sqlalchemy import insert
            from app.models import TriageResult as TriageResultModel

            await db.execute(
                insert(TriageResultModel).values(
                    incident_id=created.id,
                    severity=SeverityLevel(parsed["severity"]),
                    confidence=confidence,
                    reasoning=reasoning,
                    containment_plan=generate_containment_plan(
                        SeverityLevel(parsed["severity"])
                    ),
                    llm_provider="deterministic",
                    llm_model="deterministic-engine",
                )
            )
            await db.commit()

        except Exception as e:
            # Non-fatal: webhook succeeded even if classification fails
            print(f"Classification failed for incident {created.id}: {e}")

    return {
        "status": "processed",
        "incident_id": created.id,
        "title": created.title,
        "severity": parsed["severity"],
        "auto_classified": parsed["severity"] in ("SEV1", "SEV2"),
    }


@router.post("/opsgenie", tags=["webhook"])
async def opsgenie_webhook(
    request: Request,
) -> dict:
    """Receive and parse OpsGenie webhook events.

    Creates an incident in the timeline from the webhook payload.
    For SEV1/SEV2 alarms, automatically triggers deterministic SEV classification.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    parsed = await _parse_opsgenie_payload(payload)
    if not parsed:
        raise HTTPException(status_code=400, detail="Unrecognized OpsGenie event type")

    db_gen = get_db()
    db = await anext(db_gen)

    service = IncidentService(db)

    # Create incident from webhook data
    incident_create = IncidentCreate(
        title=parsed["title"],
        description=parsed["description"],
        raw_data=parsed["raw_data"],
        status="open",
    )

    created = await service.create_incident(incident_create)

    # Auto-trigger SEV classification for high-urgency alarms (SEV1/SEV2)
    if parsed["severity"] in ("SEV1", "SEV2"):
        try:
            classification = classify_incident(parsed["description"])

            # Create triage result from classification
            triage_result = await service.triage_incident(
                incident_id=created.id,
                use_llm=False,
            )

            # Override with deterministic classification result
            from app.models import TriageResult, SeverityLevel

            confidence = 0.95 if classification.indicators else 0.7
            reasoning = f"Auto-classified from OpsGenie webhook ({len(classification.indicators)} indicators matched)"

            from sqlalchemy import insert
            from app.models import TriageResult as TriageResultModel

            await db.execute(
                insert(TriageResultModel).values(
                    incident_id=created.id,
                    severity=SeverityLevel(parsed["severity"]),
                    confidence=confidence,
                    reasoning=reasoning,
                    containment_plan=generate_containment_plan(
                        SeverityLevel(parsed["severity"])
                    ),
                    llm_provider="deterministic",
                    llm_model="deterministic-engine",
                )
            )
            await db.commit()

        except Exception as e:
            # Non-fatal: webhook succeeded even if classification fails
            print(f"Classification failed for incident {created.id}: {e}")

    return {
        "status": "processed",
        "incident_id": created.id,
        "title": created.title,
        "severity": parsed["severity"],
        "auto_classified": parsed["severity"] in ("SEV1", "SEV2"),
    }
