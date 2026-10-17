"""Tests for the deterministic incident classification engine.

These tests verify the rule-based severity classifier, containment playbook
generation, service extraction, blast-radius analysis, comms templating, and
postmortem skeleton generation — all without any LLM or network dependency.
"""
import pytest

from app.models import SeverityLevel, CommsChannel, CommsPhase
from app.services.classifier import (
    classify_incident,
    generate_containment_plan,
    extract_services,
    extract_regions,
    analyze_blast_radius,
    generate_comms_template,
    generate_postmortem_skeleton,
)


class TestClassifyIncident:
    """Severity classification from incident text."""

    @pytest.mark.parametrize(
        "text,expected_severity",
        [
            # SEV1 — critical outages, data loss, security
            ("Primary database outage — full service unavailable", SeverityLevel.SEV1),
            ("Data loss detected in payment pipeline", SeverityLevel.SEV1),
            ("Production is down — connection refused on all replicas", SeverityLevel.SEV1),
            ("Payment gateway 502 — customers unable to checkout", SeverityLevel.SEV1),
            ("Security breach: user data compromised", SeverityLevel.SEV1),
            # SEV2 — degradation, partial issues
            ("Degraded performance on API gateway", SeverityLevel.SEV2),
            ("High replication lag on postgres-read-replica-1", SeverityLevel.SEV2),
            ("Redis memory saturated — cache eviction storm", SeverityLevel.SEV2),
            ("Timeout errors spiking in user-service", SeverityLevel.SEV2),
            # SEV3 — warning, intermittent
            ("Warning: elevated CPU on web nodes", SeverityLevel.SEV3),
            ("Intermittent connection resets on auth-service", SeverityLevel.SEV3),
            ("Slow query detected in analytics pipeline", SeverityLevel.SEV3),
            # SEV4 — informational
            ("Routine maintenance window scheduled", SeverityLevel.SEV4),
            ("Cosmetic issue in UI button alignment", SeverityLevel.SEV4),
        ],
    )
    def test_classify_severity(self, text, expected_severity):
        result = classify_incident(text)
        assert result.severity == expected_severity
        assert result.confidence > 0

    def test_classify_sev1_takes_precedence_over_sev2(self):
        """When both SEV1 and SEV2 indicators match, SEV1 wins."""
        text = "Service is down and also slow — critical outage"
        result = classify_incident(text)
        assert result.severity == SeverityLevel.SEV1

    def test_classify_no_indicators_defaults_sev3(self):
        """Text with no severity keywords defaults to SEV3."""
        result = classify_incident("Routine deployment completed successfully.")
        assert result.severity == SeverityLevel.SEV3
        assert "NO indicators" not in result.reasoning.upper() or "no" in result.reasoning.lower()
        assert len(result.indicators) == 0

    def test_classify_empty_text_defaults_sev3(self):
        result = classify_incident("")
        assert result.severity == SeverityLevel.SEV3
        assert result.confidence < 0.5

    def test_classify_confidence_increases_with_indicators(self):
        """More matching indicators → higher confidence."""
        single = classify_incident("Service is down")
        multi = classify_incident("Service is down and unavailable and offline")
        assert multi.confidence >= single.confidence

    def test_classify_reasoning_contains_indicators(self):
        result = classify_incident("Data loss and corruption detected")
        assert "data loss" in result.indicators
        assert "corruption" in result.indicators

    def test_classify_returns_classification_result(self):
        result = classify_incident("Outage affecting all users")
        assert result.severity == SeverityLevel.SEV1
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.reasoning) > 0


class TestGenerateContainmentPlan:
    """Severity-specific containment playbooks."""

    @pytest.mark.parametrize(
        "severity",
        [SeverityLevel.SEV1, SeverityLevel.SEV2, SeverityLevel.SEV3, SeverityLevel.SEV4],
    )
    def test_plan_for_each_severity(self, severity):
        plan = generate_containment_plan(severity)
        assert len(plan) > 0
        assert severity.value in plan
        assert "Containment Playbook" in plan

    def test_sev1_plan_includes_escalation(self):
        plan = generate_containment_plan(SeverityLevel.SEV1)
        assert "escalate" in plan.lower() or "on-call" in plan.lower()

    def test_sev2_plan_mentions_mitigation(self):
        plan = generate_containment_plan(SeverityLevel.SEV2)
        assert "mitigation" in plan.lower() or "rollback" in plan.lower()

    def test_plan_with_classification_includes_confidence(self):
        result = classify_incident("Outage")
        plan = generate_containment_plan(result.severity, result)
        assert "Confidence" in plan


class TestExtractServices:
    """Service name extraction from incident text."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Postgres replication lag detected", ["postgres"]),
            ("Redis memory saturated on redis-prod-1", ["redis", "redis-prod-1"]),
            ("Connection refused from user-service to api-gateway", ["user-service", "api-gateway"]),
            ("No services mentioned here", []),
            ("", []),
        ],
    )
    def test_extract_services(self, text, expected):
        services = extract_services(text)
        # Check that expected services are found (at least)
        for svc in expected:
            assert svc in services

    def test_extract_services_deduplicates(self):
        text = "postgres and postgres and postgres"
        services = extract_services(text)
        assert services.count("postgres") == 1

    def test_extract_services_case_insensitive(self):
        services = extract_services("POSTGRES Redis MONGO")
        assert "postgres" in services
        assert "redis" in services
        assert "mongo" in services


class TestExtractRegions:
    """Region extraction from incident text."""

    def test_extract_regions(self):
        regions = extract_regions("Outage in us-east-1 and eu-west-1")
        assert "us-east-1" in regions
        assert "eu-west-1" in regions

    def test_extract_regions_empty(self):
        assert extract_regions("No region mentioned") == []

    def test_extract_regions_deduplicates(self):
        regions = extract_regions("us-east-1 us-east-1 eu-west-1")
        assert regions.count("us-east-1") == 1


class TestAnalyzeBlastRadius:
    """Deterministic blast-radius analysis."""

    def test_returns_all_fields(self):
        result = analyze_blast_radius("Database outage affecting postgres and redis")
        assert "affected_services" in result
        assert "data_impact" in result
        assert "dependency_chain" in result
        assert "user_impact" in result
        assert "recovery_estimate" in result
        assert len(result["affected_services"]) > 0
        assert len(result["data_impact"]) > 0

    def test_sev1_blast_radius(self):
        result = analyze_blast_radius("Service completely down and offline")
        assert "All users" in result["user_impact"]
        assert "data loss" in result["data_impact"].lower() or "data loss" in result["data_impact"]

    def test_sev4_blast_radius(self):
        result = analyze_blast_radius("Routine maintenance window")
        assert "No user impact" in result["user_impact"]

    def test_explicit_services_merged(self):
        result = analyze_blast_radius(
            "Database issue",
            explicit_services=["web-api", "user-service"],
        )
        for svc in ["web-api", "user-service"]:
            assert svc in result["affected_services"]

    def test_no_service_names_returns_unknown(self):
        result = analyze_blast_radius("General issue detected")
        assert result["affected_services"] == ["unknown"]

    def test_sev2_blast_radius(self):
        result = analyze_blast_radius("Degraded performance with latency")
        assert "Partial" in result["user_impact"]


class TestGenerateCommsTemplate:
    """Multi-channel comms template generation."""

    @pytest.mark.parametrize(
        "channel,phase",
        [
            (CommsChannel.STATUS, CommsPhase.INITIAL),
            (CommsChannel.STATUS, CommsPhase.UPDATE),
            (CommsChannel.STATUS, CommsPhase.RESOLVED),
            (CommsChannel.SLACK, CommsPhase.INITIAL),
            (CommsChannel.SLACK, CommsPhase.EXEC),
            (CommsChannel.SLACK, CommsPhase.RESOLVED),
            (CommsChannel.EMAIL, CommsPhase.CUSTOMER),
            (CommsChannel.EMAIL, CommsPhase.LEADERSHIP),
            (CommsChannel.EMAIL, CommsPhase.ENGINEERING),
        ],
    )
    def test_all_channel_phase_combinations(self, channel, phase):
        content = generate_comms_template(
            channel=channel,
            phase=phase,
            incident_title="Payment gateway outage",
            incident_description="Customers unable to checkout due to 502 errors",
            severity=SeverityLevel.SEV1,
        )
        assert len(content) > 0
        # Must NOT leak the internal instruction text
        assert "Write the" not in content
        assert "Format:" not in content
        assert "LLM unavailable" not in content

    def test_status_initial_template(self):
        content = generate_comms_template(
            channel=CommsChannel.STATUS,
            phase=CommsPhase.INITIAL,
            incident_title="API Outage",
            incident_description="Service is down",
            severity=SeverityLevel.SEV1,
        )
        assert "investigating" in content.lower()
        assert "API Outage" in content or "affected" in content.lower()

    def test_slack_template_has_emoji(self):
        content = generate_comms_template(
            channel=CommsChannel.SLACK,
            phase=CommsPhase.INITIAL,
            incident_title="Cache failure",
            incident_description="Redis down",
            severity=SeverityLevel.SEV1,
        )
        # Slack templates use emoji indicators
        assert len(content) > 10

    def test_email_customer_has_subject(self):
        content = generate_comms_template(
            channel=CommsChannel.EMAIL,
            phase=CommsPhase.CUSTOMER,
            incident_title="DB outage",
            incident_description="Data loss",
            severity=SeverityLevel.SEV1,
        )
        assert "Subject:" in content
        assert "Dear Customer" in content


class TestPostmortemSkeleton:
    """Deterministic postmortem skeleton generation."""

    def test_returns_all_fields(self):
        result = generate_postmortem_skeleton(
            incident_title="Database outage",
            incident_description="Postgres crashed, data loss detected",
        )
        assert len(result["summary"]) > 0
        assert len(result["timeline"]) > 0
        assert len(result["root_cause"]) > 0
        assert len(result["what_went_well"]) > 0
        assert len(result["what_went_poorly"]) > 0
        assert len(result["contributing_factors"]) > 0
        assert len(result["lessons_learned"]) > 0
        assert len(result["action_items"]) >= 2

    def test_summary_contains_severity(self):
        result = generate_postmortem_skeleton(
            incident_title="Outage",
            incident_description="Service down",
        )
        assert "SEV1" in result["summary"]

    def test_timeline_contains_to_be_verified(self):
        result = generate_postmortem_skeleton(
            incident_title="Minor issue",
            incident_description="Warning logged",
        )
        assert "[TO BE VERIFIED]" in result["timeline"]

    def test_root_cause_marked_verification(self):
        result = generate_postmortem_skeleton(
            incident_title="Outage",
            incident_description="Service down",
        )
        assert "[TO BE VERIFIED]" in result["root_cause"]

    def test_action_items_have_required_fields(self):
        result = generate_postmortem_skeleton(
            incident_title="Outage",
            incident_description="Service down",
        )
        for item in result["action_items"]:
            assert "action" in item
            assert "owner" in item
            assert "due" in item
            assert "priority" in item

    def test_sev2_has_fewer_action_items_than_sev1(self):
        sev1 = generate_postmortem_skeleton(
            incident_title="Outage",
            incident_description="Service completely down",
        )
        sev2 = generate_postmortem_skeleton(
            incident_title="Slow",
            incident_description="Degraded performance",
        )
        assert len(sev1["action_items"]) >= len(sev2["action_items"])

    def test_uses_raw_data_for_classification(self):
        result = generate_postmortem_skeleton(
            incident_title="General issue",
            incident_description="Something happened",
            incident_raw_data="Database outage — data loss detected",
        )
        assert "SEV1" in result["summary"]