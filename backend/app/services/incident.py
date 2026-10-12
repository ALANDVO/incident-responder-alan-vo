from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Incident,
    TriageResult,
    BlastAnalysis,
    CommsTemplate,
    Postmortem,
    SeverityLevel,
    IncidentStatus,
    CommsChannel,
    CommsPhase,
)
from app.schemas import (
    IncidentCreate,
    IncidentUpdate,
    TriageRequest,
    BlastAnalysisRequest,
    CommsTemplateRequest,
    PostmortemRequest,
)
from app.services.llm import LLMClient, LLMProvider
from app.core.config import settings
 
 
class IncidentService:
    """Service layer for incident operations."""

    def __init__(self, db: AsyncSession, llm: Optional[LLMClient] = None):
        self.db = db
        self.llm = llm

    async def create_incident(self, data: IncidentCreate) -> Incident:
        incident = Incident(
            title=data.title,
            description=data.description,
            raw_data=data.raw_data,
            status=IncidentStatus.OPEN,
        )
        self.db.add(incident)
        await self.db.commit()
        await self.db.refresh(incident)
        return incident

    async def get_incident(self, incident_id: int) -> Optional[Incident]:
        result = await self.db.execute(
            select(Incident)
            .options(
                selectinload(Incident.triage_results),
                selectinload(Incident.blast_analyses),
                selectinload(Incident.comms_templates),
                selectinload(Incident.postmortems),
            )
            .where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()

    async def list_incidents(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[IncidentStatus] = None,
        severity: Optional[SeverityLevel] = None,
    ) -> tuple[List[Incident], int]:
        query = select(Incident)
        count_query = select(func.count(Incident.id))

        if status:
            query = query.where(Incident.status == status)
            count_query = count_query.where(Incident.status == status)
        if severity:
            query = query.where(Incident.severity == severity)
            count_query = count_query.where(Incident.severity == severity)

        query = query.order_by(Incident.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        incidents = result.scalars().all()

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return list(incidents), total

    async def update_incident(self, incident_id: int, data: IncidentUpdate) -> Optional[Incident]:
        incident = await self.get_incident(incident_id)
        if not incident:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data and update_data["status"] == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.utcnow()

        for field, value in update_data.items():
            setattr(incident, field, value)

        incident.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(incident)
        return incident

    async def delete_incident(self, incident_id: int) -> bool:
        incident = await self.get_incident(incident_id)
        if not incident:
            return False
        await self.db.delete(incident)
        await self.db.commit()
        return True

    def _build_incident_context(self, incident: Incident) -> str:
        parts = [f"Title: {incident.title}", f"Description: {incident.description}"]
        if incident.raw_data:
            parts.append(f"Raw Data:\n{incident.raw_data}")
        return "\n\n".join(parts)

    async def triage_incident(self, request: TriageRequest) -> Optional[TriageResult]:
        incident = await self.get_incident(request.incident_id)
        if not incident:
            return None

        if not self.llm or not request.use_llm:
            # Deterministic fallback
            severity = SeverityLevel.SEV3
            confidence = 0.5
            reasoning = "Fallback classification (LLM unavailable). Manual review required."
            containment = "1. Acknowledge incident\n2. Assemble response team\n3. Assess impact\n4. Implement containment\n5. Communicate to stakeholders"
        else:
            context = self._build_incident_context(incident)
            classification = await self.llm.classify(
                text=context[:6000],
                categories=[s.value for s in SeverityLevel],
                instructions="Classify incident severity based on user impact, data risk, and service criticality. ",
            )
            severity = SeverityLevel(classification.get("category", "SEV3"))
            confidence = classification.get("confidence", 0.5)
            reasoning = classification.get("reasoning", "")

            containment = await self.llm.generate(
                f"Incident data:\n{context[:6000]}\n\n"
                f"Severity: {severity.value}\n\n"
                "Suggest immediate containment steps. Prioritize by risk and reversibility. "
                "Format as numbered list. Be specific to this incident.",
                system="You are an SRE incident commander. Give actionable, specific containment steps. No generic advice.",
            )

        triage = TriageResult(
            incident_id=incident.id,
            severity=severity,
            confidence=confidence,
            reasoning=reasoning,
            containment_plan=containment,
            llm_provider=settings.llm_provider if self.llm else "fallback",
            llm_model=settings.llm_model if self.llm else "none",
        )
        self.db.add(triage)

        # Update incident severity if higher
        if incident.severity is None or self._severity_rank(severity) < self._severity_rank(incident.severity):
            incident.severity = severity
            incident.status = IncidentStatus.IN_PROGRESS

        await self.db.commit()
        await self.db.refresh(triage)
        return triage

    def _severity_rank(self, sev: SeverityLevel) -> int:
        return {"SEV1": 1, "SEV2": 2, "SEV3": 3, "SEV4": 4}[sev.value]

    async def analyze_blast_radius(self, request: BlastAnalysisRequest) -> Optional[BlastAnalysis]:
        incident = await self.get_incident(request.incident_id)
        if not incident:
            return None

        if not self.llm or not request.use_llm:
            affected_services = request.services or ["unknown"]
            data_impact = "Unknown (LLM unavailable). Manual assessment required."
            dependency_chain = "Unknown (LLM unavailable)."
            user_impact = "Unknown (LLM unavailable)."
            recovery_estimate = "Unknown (LLM unavailable)."
        else:
            context = self._build_incident_context(incident)
            services_str = ", ".join(request.services) if request.services else "auto-detect from logs"
            result = await self.llm.generate(
                f"Incident data:\n{context[:6000]}\n\n"
                f"Known services in scope: {services_str}\n\n"
                "Analyze the blast radius. Produce:\n"
                "1. AFFECTED SERVICES: list each with: what is broken, how many users affected (estimate), since when\n"
                "2. DATA IMPACT: any data loss, corruption, or at-risk data\n"
                "3. DEPENDENCY CHAIN: which downstream/upstream services are impacted and how\n"
                "4. USER IMPACT: which user segments (free/paid/enterprise), which regions, estimated count\n"
                "5. RECOVERY ESTIMATE: realistic TTR based on what is needed\n\n"
                "Be specific with numbers where the data supports it. Mark estimates as ESTIMATED.",
                system="You are an SRE mapping incident impact. Precision over pessimism — but never understate data loss risk.",
            )

            # Parse the structured response (simplified)
            affected_services = request.services or ["parsed from response"]
            data_impact = self._extract_section(result, "DATA IMPACT") or result
            dependency_chain = self._extract_section(result, "DEPENDENCY CHAIN") or ""
            user_impact = self._extract_section(result, "USER IMPACT") or ""
            recovery_estimate = self._extract_section(result, "RECOVERY ESTIMATE") or ""

        blast = BlastAnalysis(
            incident_id=incident.id,
            affected_services=affected_services,
            data_impact=data_impact,
            dependency_chain=dependency_chain,
            user_impact=user_impact,
            recovery_estimate=recovery_estimate,
            llm_provider=settings.llm_provider if self.llm else "fallback",
            llm_model=settings.llm_model if self.llm else "none",
        )
        self.db.add(blast)
        await self.db.commit()
        await self.db.refresh(blast)
        return blast

    def _extract_section(self, text: str, section: str) -> Optional[str]:
        import re
        pattern = rf"{section}:?\s*(.*?)(?=\n\d+\.|\n[A-Z ]+:$|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    async def generate_comms(self, request: CommsTemplateRequest) -> Optional[CommsTemplate]:
        incident = await self.get_incident(request.incident_id)
        if not incident:
            return None

        templates = {
            CommsChannel.STATUS: {
                CommsPhase.INITIAL: "Write the initial status page update. Format: 'We are investigating an issue affecting [service]. Impact: [what users experience]. We will update every 30 minutes. Last update: [time].' Keep it under 3 sentences. No internal jargon. Acknowledge the issue without admitting fault.",
                CommsPhase.UPDATE: "Write an in-progress status page update. Include: what has been identified, what has been done, what is next, current user impact. 3-5 sentences. Professional, transparent, no blame.",
                CommsPhase.RESOLVED: "Write the resolution status page update. Include: what happened (1 sentence), when it started and ended, what was done to fix it, what we're doing to prevent recurrence. 4-6 sentences. Grateful and forward-looking.",
            },
            CommsChannel.SLACK: {
                CommsPhase.INITIAL: "Write a Slack #inc-channel update. Start with 🚨 + one-line summary. Then: *Impact*, *Current state*, *Next steps* (3 bullets), *Who's doing what*. Max 12 lines. Engineers will read this on their phone.",
                CommsPhase.EXEC: "Write an exec summary for leadership. 5 sentences max. What happened, user impact (numbers if known), revenue impact estimate, current status, what we need from them. No technical detail they do not need.",
                CommsPhase.RESOLVED: "Write the Slack resolution update. ✅ + what was fixed, duration, user impact summary, link to postmortem (placeholder). 4-6 lines. Thank the IC team by role.",
            },
            CommsChannel.EMAIL: {
                CommsPhase.CUSTOMER: "Write a customer-facing email. Subject line + body. Formal but human. What happened, impact on their account, what we have done, what is next. Include a direct contact link. 150-250 words.",
                CommsPhase.LEADERSHIP: "Write a leadership email. Subject + body. Situation, impact (revenue + users), actions taken, actions needed, expected resolution. Include a 3-bullet 'What we need' section. 200-300 words.",
                CommsPhase.ENGINEERING: "Write an engineering all-hands email. What happened (technical, 3 sentences), what was learned, what is changing in our processes. No blame. 150-200 words.",
            },
        }

        instruction = templates.get(request.channel, {}).get(request.phase, templates[CommsChannel.STATUS][CommsPhase.INITIAL])

        if not self.llm or not request.use_llm:
            content = f"[FALLBACK TEMPLATE - LLM unavailable]\n\n{instruction}\n\nIncident: {incident.title}"
        else:
            context = self._build_incident_context(incident)
            content = await self.llm.generate(
                f"Incident data:\n{context[:4000]}\n\n{instruction}\n\n"
                "Use only facts present in the incident data. Where specifics are missing, use [BRACKETED PLACEHOLDER]. Do not invent service names, user counts, or timestamps not in the data.",
                system="You write incident communications. Clear, calm, factual. Never blame individuals. Never overpromise. Every sentence must be defensible in a postmortem.",
            )

        comms = CommsTemplate(
            incident_id=incident.id,
            channel=request.channel,
            phase=request.phase,
            content=content,
            llm_provider=settings.llm_provider if self.llm else "fallback",
            llm_model=settings.llm_model if self.llm else "none",
        )
        self.db.add(comms)
        await self.db.commit()
        await self.db.refresh(comms)
        return comms

    async def generate_postmortem(self, request: PostmortemRequest) -> Optional[Postmortem]:
        incident = await self.get_incident(request.incident_id)
        if not incident:
            return None

        if not self.llm or not request.use_llm:
            summary = "Postmortem generation unavailable (LLM not configured)."
            timeline = "Timeline reconstruction requires LLM."
            root_cause = "Root cause analysis requires LLM."
            what_went_well = "Team responded promptly."
            what_went_poorly = "Insufficient monitoring/alerting."
            contributing_factors = "Systemic factors to be analyzed."
            action_items = [
                {"id": 1, "action": "Add monitoring for X", "owner": "Team", "due": "2024-01-01", "priority": "high"},
                {"id": 2, "action": "Update runbook", "owner": "Team", "due": "2024-01-15", "priority": "medium"},
            ]
            lessons_learned = "1. Improve observability\n2. Practice incident response"
        else:
            context = self._build_incident_context(incident)
            result = await self.llm.generate(
                f"Incident data:\n{context[:6000]}\n\n"
                "Generate a post-incident review document with these sections:\n"
                "## Summary (5 sentences: what, when, impact, root cause, resolution)\n"
                "## Timeline (table: | Time | Event | Detector |) — reconstruct from the data\n"
                "## Root Cause Analysis (5-Why chain if data supports it, otherwise hypothesis)\n"
                "## What Went Well (specific, credited to teams/roles)\n"
                "## What Went Poorly (specific, no blame)\n"
                "## Contributing Factors (systemic, not individual)\n"
                "## Action Items (table: | # | Action | Owner | Due | Priority |) — 4-8 items\n"
                "## Lessons Learned (3-5 actionable takeaways)\n\n"
                "Mark anything not supported by the data as [TO BE VERIFIED]. Do not fabricate timeline entries.",
                system="You write blameless postmortems. Focus on systems and processes, not people. Every action item must be concrete and assignable.",
            )

            # Parse sections (simplified)
            summary = self._extract_section(result, "Summary") or result[:500]
            timeline = self._extract_section(result, "Timeline") or ""
            root_cause = self._extract_section(result, "Root Cause") or ""
            what_went_well = self._extract_section(result, "What Went Well") or ""
            what_went_poorly = self._extract_section(result, "What Went Poorly") or ""
            contributing_factors = self._extract_section(result, "Contributing Factors") or ""
            action_items = self._parse_action_items(self._extract_section(result, "Action Items") or "")
            lessons_learned = self._extract_section(result, "Lessons Learned") or ""

        postmortem = Postmortem(
            incident_id=incident.id,
            summary=summary,
            timeline=timeline,
            root_cause=root_cause,
            what_went_well=what_went_well,
            what_went_poorly=what_went_poorly,
            contributing_factors=contributing_factors,
            action_items=action_items,
            lessons_learned=lessons_learned,
            llm_provider=settings.llm_provider if self.llm else "fallback",
            llm_model=settings.llm_model if self.llm else "none",
        )
        self.db.add(postmortem)
        await self.db.commit()
        await self.db.refresh(postmortem)
        return postmortem

    def _parse_action_items(self, text: str) -> List[dict]:
        items = []
        import re
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "|" in line and not line.strip().startswith("|---"):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 5 and parts[0].isdigit():
                    items.append({
                        "id": int(parts[0]),
                        "action": parts[1],
                        "owner": parts[2],
                        "due": parts[3],
                        "priority": parts[4],
                    })
        if not items:
            items = [
                {"id": 1, "action": "Review incident response process", "owner": "Team Lead", "due": "2024-01-15", "priority": "high"},
                {"id": 2, "action": "Improve monitoring coverage", "owner": "SRE", "due": "2024-01-31", "priority": "high"},
            ]
        return items

