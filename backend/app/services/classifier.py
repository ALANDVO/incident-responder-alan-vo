"""Deterministic incident classification engine.

Offline rule-based severity classification, blast-radius service extraction,
containment playbook generation, and multi-channel comms templating.  No LLM
or network dependency is required — the engine works entirely from incident
text via keyword and pattern matching.

This is the deterministic offline baseline; the LLM path is an advisory
augmentation that may refine (but never replace) these results.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app.models import SeverityLevel, CommsChannel, CommsPhase


@dataclass
class ClassificationResult:
    """Result of deterministic incident classification."""

    severity: SeverityLevel
    confidence: float
    reasoning: str
    indicators: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Severity indicator patterns — ordered most- to least-severe.
# Each pattern is a compiled regex matched case-insensitively against the
# normalized incident text.  Patterns are grouped per severity level.
# ---------------------------------------------------------------------------
_SEVERITY_PATTERNS: List[tuple] = [
    (
        SeverityLevel.SEV1,
        [
            r"\boutage\b",
            r"\bcomplete outage\b",
            r"\btotal outage\b",
            r"\bservices? down\b",
            r"\bis down\b",
            r"\bdown\b",
            r"\bunavailable\b",
            r"\bunreachable\b",
            r"\boffline\b",
            r"\bcrashed\b",
            r"\bcrash(ed)?\b",
            r"\bno quorum\b",
            r"\bsplit\s*brain\b",
            r"\bdata loss\b",
            r"\bdata corruption\b",
            r"\bcorrupt(ed|ion)?\b",
            r"\bbreach\b",
            r"\bcompromised\b",
            r"\bdenial of service\b",
            r"\bconnection refused\b",
            r"\bunable to access\b",
            r"\ball users?\b",
            r"\ball regions?\b",
            r"\bcritical\b",
            r"\b502\b",
            r"\b500 internal\b",
            r"\bunable to\b",
            r"\bcannot (reach|connect|serve)\b",
            r"\btotal service failure\b",
        ],
    ),
    (
        SeverityLevel.SEV2,
        [
            r"\bdegraded( performance)?\b",
            r"\bresponse slow\b",
            r"\bslowly\b",
            r"\bhigh latency\b",
            r"\blatency\b",
            r"\btimeout\b",
            r"\btimeouts\b",
            r"\bfailing\b",
            r"\bfailure(s)?\b",
            r"\boverload(ed)?\b",
            r"\bthrottling\b",
            r"\bsaturated\b",
            r"\breviction storm\b",
            r"\bdegradation\b",
            r"\btiming out\b",
            r"\breplication lag\b",
            r"\bdisk full\b",
            r"\bpartial outage\b",
            r"\belevated error\b",
            r"\berror rate\b",
            r"\b503\b",
            r"\bservice degraded\b",
            r"\berrors? spik(e|ing)\b",
        ],
    ),
    (
        SeverityLevel.SEV3,
        [
            r"\bwarning\b",
            r"\bintermittent\b",
            r"\bflapping\b",
            r"\bslow query\b",
            r"\bretr(y|ied|ies)\b",
            r"\breconnection\b",
            r"\bpool exhaust(ed)?\b",
            r"\bminor degradation\b",
            r"\belevated\b",
        ],
    ),
    (
        SeverityLevel.SEV4,
        [
            r"\binformational\b",
            r"\bcosmetic\b",
            r"\broutine maintenance\b",
            r"\blog noise\b",
            r"\bdeprecated\b",
            r"\bslowness\b",
            r"\bmaintenance\b",
        ],
    ),
]

# Base confidence per severity level (boosted by indicator count).
_BASE_CONFIDENCE: Dict[SeverityLevel, float] = {
    SeverityLevel.SEV1: 0.80,
    SeverityLevel.SEV2: 0.65,
    SeverityLevel.SEV3: 0.45,
    SeverityLevel.SEV4: 0.25,
}

# Impact keywords that confirm severity (raise confidence).
_IMPACT_KEYWORDS = [
    r"\bcustomers?\b",
    r"\busers?\b",
    r"\bcheckout\b",
    r"\bpayment\b",
    r"\bauth",
    r"\blogin\b",
    r"\bbilling\b",
    r"\bapi\b",
    r"\bdatabase\b",
]


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace for pattern matching."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _compiled_patterns() -> List[tuple]:
    """Return (severity, [compiled_patterns]) lazily compiled once."""
    compiled: List[tuple] = []
    for severity, patterns in _SEVERITY_PATTERNS:
        compiled.append(
            (severity, [re.compile(p, re.IGNORECASE) for p in patterns])
        )
    return compiled


_COMPILED = _compiled_patterns()


def classify_incident(text: str) -> ClassificationResult:
    """Classify incident severity from free-form text.

    Scans for severity indicators ordered from most to least severe.  The
    first severity level with **any** matching indicator wins; among matches
    at that level, confidence is boosted by indicator count and the presence
    of impact keywords.

    Args:
        text: Incident title, description, and raw data joined together.

    Returns:
        ClassificationResult with severity, confidence (0–1), reasoning,
        and the matched indicators.
    """
    if not text or not text.strip():
        return ClassificationResult(
            severity=SeverityLevel.SEV3,
            confidence=0.10,
            reasoning="No incident text provided; defaulting to SEV3 for manual review.",
            indicators=[],
        )

    text = _normalize(text)
    indicators: List[str] = []
    matched_severity: Optional[SeverityLevel] = None

    for severity, patterns in _COMPILED:
        for pat in patterns:
            match = pat.search(text)
            if match:
                indicators.append(match.group(0))
                if matched_severity is None:
                    matched_severity = severity

    if matched_severity is None:
        return ClassificationResult(
            severity=SeverityLevel.SEV3,
            confidence=0.30,
            reasoning=(
                "No severity indicators matched; defaulting to SEV3 for "
                "manual review. No keywords for outage, degradation, "
                "warning, or informational severity were found."
            ),
            indicators=[],
        )

    # Confidence: base for the level, boosted by indicator count.
    base = _BASE_CONFIDENCE[matched_severity]
    boost = min(0.15, 0.03 * len(indicators))
    # Impact keywords further confirm severity.
    impact_matches = sum(
        1 for kw in _IMPACT_KEYWORDS if re.search(kw, text, re.IGNORECASE)
    )
    impact_boost = min(0.10, 0.02 * impact_matches)
    confidence = min(0.95, round(base + boost + impact_boost, 2))

    reasoning = (
        f"Matched {len(indicators)} severity indicator(s) for "
        f"{matched_severity.value}: {', '.join(indicators[:5])}"
        f"{'...' if len(indicators) > 5 else ''}. "
        f"Impact keywords: {impact_matches} match(es)."
    )

    return ClassificationResult(
        severity=matched_severity,
        confidence=confidence,
        reasoning=reasoning,
        indicators=indicators,
    )


# ---------------------------------------------------------------------------
# Containment playbooks — severity-specific, with incident-type awareness.
# ---------------------------------------------------------------------------
_CONTAINMENT_PLAYBOOKS: Dict[SeverityLevel, List[str]] = {
    SeverityLevel.SEV1: [
        "Acknowledge incident and escalate to on-call SRE/engineering lead immediately.",
        "Create/#join dedicated incident-response channel; set up war room.",
        "If data integrity is at risk, halt writes or execute controlled service shutdown.",
        "Begin backup restoration or failover to standby region/replica.",
        "Activate status page / customer comms within 5 minutes.",
        "Continuously update stakeholders every 15 minutes until resolution.",
    ],
    SeverityLevel.SEV2: [
        "Acknowledge incident and page on-call engineer.",
        "Create incident tracking thread with severity and initial impact.",
        "Identify and isolate affected components / services.",
        "Begin mitigation: rollback recent deploy, scale up, or apply rate limiting.",
        "Monitor key metrics (latency, error rate, saturation) for recovery.",
        "Post initial status update to affected users within 15 minutes.",
    ],
    SeverityLevel.SEV3: [
        "Log incident in tracking system with severity SEV3.",
        "Gather context: review recent changes, logs, and monitoring dashboards.",
        "If a straightforward fix exists, implement and verify within 1 hour.",
        "Schedule deeper investigation during the next business day.",
        "Document findings and add to knowledge base.",
    ],
    SeverityLevel.SEV4: [
        "Log incident as informational for tracking.",
        "Add to next sprint backlog for review.",
        "Verify the issue does not recur in monitoring for 48 hours.",
    ],
}


def generate_containment_plan(
    severity: SeverityLevel,
    classification: Optional[ClassificationResult] = None,
) -> str:
    """Generate a severity-specific containment playbook as numbered text."""
    steps = _CONTAINMENT_PLAYBOOKS.get(severity, _CONTAINMENT_PLAYBOOKS[SeverityLevel.SEV3])
    lines = [f"{i + 1}. {step}" for i, step in enumerate(steps)]
    header = (
        f"Containment Playbook — {severity.value}\n"
        f"Confidence: {classification.confidence:.0%} ({classification.reasoning})"
        if classification
        else f"Containment Playbook — {severity.value}"
    )
    return header + "\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Service extraction for blast-radius analysis.
# ---------------------------------------------------------------------------
_SERVICE_PATTERNS = [
    re.compile(r"\b(postgres(?:ql)?|mysql|redis|mongo(?:db)?|elastic(?:search)?|kafka|zookeeper|rabbitmq|memcache(?:hed)?)\b", re.IGNORECASE),
    re.compile(r"\b(nginx|envoy|haproxy|traefik|caddy)\b", re.IGNORECASE),
    re.compile(r"\b([\w-]+service)\b", re.IGNORECASE),
    re.compile(r"\b(web-api|api-gateway|payment[-_]?gateway|auth[-_]?service|user-service)\b", re.IGNORECASE),
    re.compile(r"\b([a-z]+-read-replica-\d+)\b", re.IGNORECASE),
    re.compile(r"\b(redis-[a-z0-9-]+)\b", re.IGNORECASE),
]

_REGION_PATTERNS = [
    re.compile(r"\b(us-east-1|us-west-1|us-west-2|eu-west-1|eu-central-1|ap-southeast-1|ap-northeast-1|sa-east-1)\b", re.IGNORECASE),
    re.compile(r"\b(us-east|us-west|eu-west|eu-central|apac|emea|americas|global)\b", re.IGNORECASE),
]


def extract_services(text: str) -> List[str]:
    """Extract infrastructure service names from incident text."""
    if not text:
        return []
    found: List[str] = []
    for pat in _SERVICE_PATTERNS:
        for match in pat.findall(text):
            if isinstance(match, tuple):
                name = match[0]
            else:
                name = match
            if name:
                name = name.lower()
                if name not in found:
                    found.append(name)
    return found


def extract_regions(text: str) -> List[str]:
    """Extract cloud regions from incident text."""
    if not text:
        return []
    found: List[str] = []
    for pat in _REGION_PATTERNS:
        for match in pat.findall(text):
            if isinstance(match, tuple):
                name = match[0]
            else:
                name = match
            if name and name not in found:
                found.append(name)
    return found


def analyze_blast_radius(
    text: str,
    explicit_services: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute deterministic blast-radius estimates from incident text."""
    services = extract_services(text)
    if explicit_services:
        for svc in explicit_services:
            if svc and svc not in services:
                services.append(svc)
    if not services:
        services = ["unknown"]

    regions = extract_regions(text)
    region_text = ", ".join(regions) if regions else "region not identified"

    # Rough impact estimate based on severity indicators.
    classification = classify_incident(text)
    sev = classification.severity

    if sev == SeverityLevel.SEV1:
        user_impact = "All users / 100% of traffic affected."
        data_impact = "Potential data loss or corruption. Investigate immediately."
        recovery = "2–4 hours: service restoration via failover and backup recovery."
    elif sev == SeverityLevel.SEV2:
        user_impact = "Partial user impact. Some regions or cohorts affected."
        data_impact = "No confirmed data loss; monitor for integrity issues."
        recovery = "30–90 minutes: mitigation and root-cause investigation."
    elif sev == SeverityLevel.SEV4:
        user_impact = "No user impact. Internal or informational."
        data_impact = "No data impact."
        recovery = "< 24 hours: planned fix in next release."
    else:
        user_impact = "Some user impact. Monitoring for escalation."
        data_impact = "No confirmed data loss."
        recovery = "1–2 hours: investigate and contain."

    return {
        "affected_services": services,
        "data_impact": data_impact,
        "dependency_chain": f"Affected components: {', '.join(services)}. Propagate impact to dependent services; verify upstream/downstream connections.",
        "user_impact": user_impact,
        "recovery_estimate": recovery,
        "region": region_text,
        "confidence": classification.confidence,
    }


# ---------------------------------------------------------------------------
# Multi-channel communications templates.
# ---------------------------------------------------------------------------
_COMMS_TEMPLATES: Dict[CommsChannel, Dict[CommsPhase, str]] = {
    CommsChannel.STATUS: {
        CommsPhase.INITIAL: (
            "We are investigating an issue affecting {service}. "
            "Impact: {impact}. "
            "We have identified the affected components and are working on a resolution. "
            "We will update every 30 minutes. Last update: {timestamp}."
        ),
        CommsPhase.UPDATE: (
            "Update on the ongoing incident affecting {service}. "
            "What we identified: {root_cause}. "
            "What we have done: {actions}. "
            "Current impact: {impact}. "
            "Next steps: {next_steps}. Last update: {timestamp}."
        ),
        CommsPhase.RESOLVED: (
            "Resolved: The incident affecting {service} has been resolved. "
            "It started at {start_time} and ended at {end_time}. "
            "What happened: {summary}. "
            "What we have done to fix it: {actions}. "
            "We are implementing changes to prevent recurrence. Last update: {timestamp}."
        ),
    },
    CommsChannel.SLACK: {
        CommsPhase.INITIAL: (
            ":rotating_light: {title}\n"
            "*Impact*: {impact}\n"
            "*Current state*: {state}\n"
            "*Next steps*: {next_steps}\n"
            "*Who's doing what*: On-call SRE investigating, support shadowing."
        ),
        CommsPhase.UPDATE: (
            ":information_source: Update — {title}\n"
            "*Identified*: {root_cause}\n"
            "*Actions taken*: {actions}\n"
            "*Current impact*: {impact}\n"
            "*ETA*: {eta}"
        ),
        CommsPhase.RESOLVED: (
            ":white_check_mark: Resolved — {title}\n"
            "*Fixed*: {actions}\n"
            "*Duration*: {duration}\n"
            "*User impact*: {impact}\n"
            "*Postmortem*: [link]"
        ),
        CommsPhase.EXEC: (
            "Summary: {title}\n"
            "User impact: {impact}\n"
            "Current status: {state}\n"
            "Need from leadership: {needs}"
        ),
    },
    CommsChannel.EMAIL: {
        CommsPhase.CUSTOMER: (
            "Subject: Service issue notification — {service}\n\n"
            "Dear Customer,\n\n"
            "We are aware of an issue affecting {service}. "
            "Impact: {impact}.\n\n"
            "What we are doing:\n{actions}\n\n"
            "We will update you every 30 minutes. "
            "If you have questions, contact support@example.com.\n\n"
            "Thank you for your patience."
        ),
        CommsPhase.LEADERSHIP: (
            "Subject: Incident Summary — {service} — {severity}\n\n"
            "Situation: {summary}\n"
            "Revenue/user impact: {impact}\n"
            "Actions taken: {actions}\n"
            "What we need: {needs}\n"
            "Expected resolution: {eta}"
        ),
        CommsPhase.ENGINEERING: (
            "Subject: Post-incident review — {service}\n\n"
            "What happened (technical): {summary}\n"
            "Root cause: {root_cause}\n"
            "What we learned: {lessons}\n"
            "Process changes: {actions}"
        ),
    },
}

_COMMS_DEFAULT_PHASE: Dict[CommsChannel, CommsPhase] = {
    CommsChannel.STATUS: CommsPhase.INITIAL,
    CommsChannel.SLACK: CommsPhase.INITIAL,
    CommsChannel.EMAIL: CommsPhase.CUSTOMER,
}


def generate_comms_template(
    channel: CommsChannel,
    phase: CommsPhase,
    incident_title: str,
    incident_description: str,
    severity: SeverityLevel,
    classification: Optional[ClassificationResult] = None,
) -> str:
    """Generate a multi-channel comms template from incident data."""
    services = extract_services(incident_title + "\n" + incident_description)
    service_str = ", ".join(services) if services else "affected services"
    classification = classification or classify_incident(
        incident_title + "\n" + incident_description
    )

    # Impact summary from classification.
    impact = _impact_summary(severity)
    root_cause = "Under investigation."
    actions = "Response team assembled and investigating."
    next_steps = "Continuously monitoring and working toward resolution."
    state = f"Active — {severity.value} severity incident in progress."
    needs = "Approval to engage customer communications."
    eta = "Next update within 30 minutes."
    duration = "Ongoing."
    summary = incident_description[:200]
    lesson = "Improve monitoring and alerting coverage."
    timestamp = "2026-01-01T00:00:00Z"
    start_time = timestamp
    end_time = timestamp

    replacements: Dict[str, str] = {
        "service": service_str,
        "title": incident_title,
        "impact": impact,
        "root_cause": root_cause,
        "actions": actions,
        "next_steps": next_steps,
        "state": state,
        "needs": needs,
        "eta": eta,
        "duration": duration,
        "summary": summary,
        "lessons": lesson,
        "timestamp": timestamp,
        "start_time": start_time,
        "end_time": end_time,
        "severity": severity.value,
    }

    template = _COMMS_TEMPLATES.get(channel, {}).get(
        phase,
        _COMMS_TEMPLATES[CommsChannel.STATUS][CommsPhase.INITIAL],
    )

    content = template.format(**replacements)
    return content


def _impact_summary(severity: SeverityLevel) -> str:
    """Human-readable impact description per severity."""
    return {
        SeverityLevel.SEV1: "All users and traffic affected across all regions.",
        SeverityLevel.SEV2: "Partial degradation affecting some users or regions.",
        SeverityLevel.SEV3: "Minor impact; some users may experience issues.",
        SeverityLevel.SEV4: "No user impact. Internal or informational.",
    }.get(severity, "Impact under assessment.")


def generate_postmortem_skeleton(
    incident_title: str,
    incident_description: str,
    incident_raw_data: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a deterministic postmortem skeleton from incident data.

    Reconstructs a timeline, root-cause hypothesis, and action items from
    incident text and severity classification.  Values not supported by the
    data are explicitly marked as **[TO BE VERIFIED]**.
    """
    full_text = incident_title + "\n" + incident_description
    if incident_raw_data:
        full_text += "\n" + incident_raw_data
    classification = classify_incident(full_text)
    services = extract_services(full_text)
    service_str = ", ".join(services) if services else "unspecified"
    impact = _impact_summary(classification.severity)

    indicators_str = (
        ", ".join(classification.indicators[:5])
        if classification.indicators
        else "none"
    )

    summary = (
        f"Incident '{incident_title}' classified as {classification.severity.value} "
        f"(confidence {classification.confidence:.0%}). "
        f"Impact: {impact}. "
        f"Services indicated: {service_str}."
    )

    timeline = (
        f"1. Incident detected at {datetime.now(tz=timezone.utc).isoformat()}Z - alert triggered.\n"
        f"2. Initial triage - severity {classification.severity.value} assigned by deterministic engine.\n"
        f"3. Response team engaged - containment plan activated.\n"
        f"4. Resolution - in progress / [TO BE VERIFIED]"
    )

    root_cause = (
        f"Deterministic analysis identified severity indicators: {indicators_str}. "
        f"Root cause: [TO BE VERIFIED] — requires manual analysis of {service_str} logs."
    )

    if classification.confidence >= 0.7:
        what_went_well = (
            "Severity correctly classified via the deterministic engine. "
            "Response team assembled promptly."
        )
        what_went_poorly = "Monitoring did not auto-correlate the alert."
    else:
        what_went_well = "Response team assembled promptly."
        what_went_poorly = (
            "Severity classification had low confidence. "
            "Consider manual review of alert quality and detection coverage."
        )

    contributing_factors = (
        "Insufficient automated blast-radius detection. "
        "Runbook gaps in containment handoff. "
        "Alert did not surface affected-service topology."
    )

    action_items = _severity_action_items(classification.severity)

    lessons_learned = (
        f"1. Ensure on-call has access to the deterministic triage engine.\n"
        f"2. Review whether the {classification.severity.value} classification matched actual impact.\n"
        f"3. Add service-name correlation to alert pipelines to improve blast-radius accuracy."
    )

    return {
        "summary": summary,
        "timeline": timeline,
        "root_cause": root_cause,
        "what_went_well": what_went_well,
        "what_went_poorly": what_went_poorly,
        "contributing_factors": contributing_factors,
        "action_items": action_items,
        "lessons_learned": lessons_learned,
    }


def _severity_action_items(severity: SeverityLevel) -> List[Dict[str, str]]:
    """Return recommended action items for a given severity level."""
    items: Dict[SeverityLevel, List[Dict[str, str]]] = {
        SeverityLevel.SEV1: [
            {"id": 1, "action": "Conduct blameless postmortem within 72 hours", "owner": "Incident Commander", "due": "72h", "priority": "high"},
            {"id": 2, "action": "Implement automated failover for affected services", "owner": "SRE Team", "due": "2 weeks", "priority": "high"},
            {"id": 3, "action": "Add data-loss detection to monitoring stack", "owner": "Platform Team", "due": "1 month", "priority": "high"},
            {"id": 4, "action": "Review and update on-call escalation paths", "owner": "Engineering Manager", "due": "1 week", "priority": "medium"},
        ],
        SeverityLevel.SEV2: [
            {"id": 1, "action": "Conduct postmortem within 5 business days", "owner": "Incident Commander", "due": "5d", "priority": "high"},
            {"id": 2, "action": "Add latency/error-rate alerting for affected services", "owner": "SRE Team", "due": "1 week", "priority": "high"},
            {"id": 3, "action": "Review runbook for this incident type", "owner": "On-Call Engineer", "due": "1 week", "priority": "medium"},
        ],
        SeverityLevel.SEV3: [
            {"id": 1, "action": "Track in backlog for next sprint review", "owner": "On-Call Engineer", "due": "next sprint", "priority": "medium"},
            {"id": 2, "action": "Add monitoring if none exists", "owner": "SRE Team", "due": "2 weeks", "priority": "low"},
        ],
        SeverityLevel.SEV4: [
            {"id": 1, "action": "Log and monitor for 48 hours", "owner": "SRE Team", "due": "48h", "priority": "low"},
        ],
    }
    return items.get(severity, items[SeverityLevel.SEV3])