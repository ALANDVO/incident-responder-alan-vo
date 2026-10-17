"""Incident workflows and domain engine tests.

Covers:
  * Health check endpoint
  * Incident creation, listing, detail, update, delete
  * Triage deterministic analysis (SEV classification + containment steps)
  * Blast radius dependency graph analysis
  * Multi-channel communications generation (Status, Slack, Email)
  * Retrospective postmortem generation
  * Malformed / boundary input handling
"""
import pytest
from tests.conftest import bearer


@pytest.mark.anyio
async def test_health_check(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


@pytest.mark.anyio
async def test_llm_providers_endpoint(client):
    resp = await client.get("/api/llm/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "openai" in data["providers"]
    assert "gemini" in data["providers"]


@pytest.mark.anyio
async def test_create_and_get_incident(client, auth_token):
    token = await auth_token(email="op1@example.com", role="operator")
    resp = await client.post(
        "/api/incidents",
        json={
            "title": "Primary Database Replication Lag",
            "description": "High replication lag detected on postgres-read-replica-1",
            "raw_data": "WARN: lag > 60s across replica cluster",
        },
        headers=bearer(token),
    )
    assert resp.status_code == 201
    incident = resp.json()
    assert incident["id"] > 0
    assert incident["title"] == "Primary Database Replication Lag"
    assert incident["status"] == "open"

    # View incident as viewer
    viewer_token = await auth_token(email="view1@example.com", role="viewer")
    get_resp = await client.get(f"/api/incidents/{incident['id']}", headers=bearer(viewer_token))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == incident["id"]


@pytest.mark.anyio
async def test_list_and_filter_incidents(client, auth_token):
    token = await auth_token(email="op2@example.com", role="operator")
    for i in range(3):
        await client.post(
            "/api/incidents",
            json={"title": f"Incident {i}", "description": f"Details {i}"},
            headers=bearer(token),
        )

    resp = await client.get("/api/incidents?page=1&page_size=10", headers=bearer(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) >= 3


@pytest.mark.anyio
async def test_update_incident_status(client, auth_token):
    token = await auth_token(email="op3@example.com", role="operator")
    resp = await client.post(
        "/api/incidents",
        json={"title": "Network outage", "description": "Switch packet drop"},
        headers=bearer(token),
    )
    incident_id = resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/incidents/{incident_id}",
        json={"status": "resolved"},
        headers=bearer(token),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "resolved"
    assert patch_resp.json()["resolved_at"] is not None


@pytest.mark.anyio
async def test_triage_incident_deterministic(client, auth_token):
    token = await auth_token(email="op4@example.com", role="operator")
    resp = await client.post(
        "/api/incidents",
        json={"title": "Payment gateway 502", "description": "Customers unable to checkout"},
        headers=bearer(token),
    )
    incident_id = resp.json()["id"]

    triage_resp = await client.post(
        f"/api/incidents/{incident_id}/triage",
        json={"incident_id": incident_id, "use_llm": False},
        headers=bearer(token),
    )
    assert triage_resp.status_code == 200
    triage_data = triage_resp.json()
    assert triage_data["incident_id"] == incident_id
    assert triage_data["severity"] == "SEV1"
    assert len(triage_data["containment_plan"]) > 0
    assert "Containment Playbook" in triage_data["containment_plan"]
    assert "Deterministic" in triage_data["reasoning"]
    assert triage_data["llm_provider"] == "fallback"


@pytest.mark.anyio
async def test_blast_radius_analysis_deterministic(client, auth_token):
    token = await auth_token(email="op5@example.com", role="operator")
    resp = await client.post(
        "/api/incidents",
        json={"title": "Cache eviction storm", "description": "Redis memory saturated"},
        headers=bearer(token),
    )
    incident_id = resp.json()["id"]

    blast_resp = await client.post(
        f"/api/incidents/{incident_id}/blast",
        json={
            "incident_id": incident_id,
            "services": ["cache", "web-api", "user-service"],
            "use_llm": False,
        },
        headers=bearer(token),
    )
    assert blast_resp.status_code == 200
    blast_data = blast_resp.json()
    assert "cache" in blast_data["affected_services"]
    assert "redis" in blast_data["affected_services"]
    assert "Unknown (LLM unavailable)" not in blast_data["data_impact"]
    assert "Affected components" in blast_data["dependency_chain"]
    assert blast_data["incident_id"] == incident_id


@pytest.mark.anyio
async def test_comms_template_generation_deterministic(client, auth_token):
    token = await auth_token(email="op6@example.com", role="operator")
    resp = await client.post(
        "/api/incidents",
        json={"title": "CDN degradation", "description": "Asset downloads timing out"},
        headers=bearer(token),
    )
    incident_id = resp.json()["id"]

    comms_resp = await client.post(
        f"/api/incidents/{incident_id}/comms",
        json={
            "incident_id": incident_id,
            "channel": "status",
            "phase": "initial",
            "use_llm": False,
        },
        headers=bearer(token),
    )
    assert comms_resp.status_code == 200
    comms_data = comms_resp.json()
    assert comms_data["channel"] == "status"
    assert comms_data["phase"] == "initial"
    assert len(comms_data["content"]) > 0
    assert "LLM unavailable" not in comms_data["content"]
    assert "Write the" not in comms_data["content"]
    assert "investigating" in comms_data["content"].lower()


@pytest.mark.anyio
async def test_postmortem_generation_deterministic(client, auth_token):
    token = await auth_token(email="op7@example.com", role="operator")
    resp = await client.post(
        "/api/incidents",
        json={"title": "DNS resolve error", "description": "CoreDNS pods crashed"},
        headers=bearer(token),
    )
    incident_id = resp.json()["id"]

    pm_resp = await client.post(
        f"/api/incidents/{incident_id}/postmortem",
        json={"incident_id": incident_id, "use_llm": False},
        headers=bearer(token),
    )
    assert pm_resp.status_code == 200
    pm_data = pm_resp.json()
    assert pm_data["incident_id"] == incident_id
    assert len(pm_data["summary"]) > 0
    assert len(pm_data["timeline"]) > 0
    assert "SEV1" in pm_data["summary"]
    assert "[TO BE VERIFIED]" in pm_data["root_cause"]
    assert len(pm_data["action_items"]) >= 2


@pytest.mark.anyio
async def test_delete_incident(client, auth_token):
    token = await auth_token(email="op8@example.com", role="operator")
    resp = await client.post(
        "/api/incidents",
        json={"title": "Temporary incident", "description": "To be removed"},
        headers=bearer(token),
    )
    incident_id = resp.json()["id"]

    del_resp = await client.delete(f"/api/incidents/{incident_id}", headers=bearer(token))
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/incidents/{incident_id}", headers=bearer(token))
    assert get_resp.status_code == 404
