"""Webhook ingestion tests for PagerDuty and OpsGenie.

Verifies that automated alerts are parsed into the incident timeline and that
high-urgency (SEV1/SEV2) alarms trigger deterministic SEV classification.
"""
import pytest
import os
import tempfile
import pathlib
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(autouse=True)
def isolated_db():
    """Per-test isolated SQLite DB using conftest pattern."""
    _tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="ir-wh-test-"))
    db_path = str(_tmpdir / "test.db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"

    import app.core.database as _dbmod
    _original_engine = _dbmod.engine
    _original_sessions = _dbmod.async_session_maker

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    _dbmod.engine = engine
    _dbmod.async_session_maker = session_maker

    try:
        from app.models import Base
        async def _create_all():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        import asyncio
        asyncio.run(_create_all())
        yield
    finally:
        asyncio_task = engine.dispose()
        _dbmod.engine = _original_engine
        _dbmod.async_session_maker = _original_sessions


@pytest.mark.anyio
async def test_pagerduty_sev1_webhook_creates_incident(client):
    """PagerDuty SEV1 webhook creates incident in timeline."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        # PagerDuty v2 webhook payload with correct structure
        pd_payload = {
            "event_type": "pd.event.problem.created",
            "payload": {
                "severity": "critical",
                "title": "Database connection pool exhausted",
                "incident": {
                    "url": "https://events.pagerduty.com/incidents/12345",
                    "status": "triggered",
                    "priority": {"id": "P1", "summary": "P1"},
                    "service": {"name": "Production DB"},
                },
                "routing_rule": {"name": "critical-severity"},
            }
        }

        resp = await http.post(
            "/api/webhook/pagerduty",
            json=pd_payload,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Verify incident was created
        assert data["incident_id"] > 0
        assert data["title"] == "Database connection pool exhausted"
        assert data["severity"] == "SEV1"
        assert data["auto_classified"] is True


@pytest.mark.anyio
async def test_pagerduty_sev4_webhook_creates_incident(client):
    """PagerDuty SEV4 webhook creates incident but does NOT auto-trigger classification."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        pd_payload = {
            "event_type": "pd.event.problem.created",
            "payload": {
                "severity": "low",
                "title": "Low disk space warning",
                "incident": {
                    "url": "https://events.pagerduty.com/incidents/67890",
                    "status": "triggered",
                    "priority": {"id": "P4", "summary": "P4"},
                    "service": {"name": "Production Server"},
                },
                "routing_rule": {"name": "low-severity"},
            }
        }

        resp = await http.post(
            "/api/webhook/pagerduty",
            json=pd_payload,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Verify incident was created
        assert data["incident_id"] > 0
        assert data["title"] == "Low disk space warning"
        assert data["severity"] == "SEV4"
        assert data["auto_classified"] is False


@pytest.mark.anyio
async def test_opsgenie_sev2_webhook_creates_incident(client):
    """OpsGenie P2 (SEV2) webhook creates incident in timeline."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        og_payload = {
            "alert": {
                "name": "High CPU utilization on app-server",
                "priority": "P2",
                "state": "WARNING",
                "message": "CPU usage has been above 90% for 5 minutes",
                "source": {"type": "host", "name": "app-server-1"},
                "details": {"cpu_usage": "92%", "threshold": "80%"},
            }
        }

        resp = await http.post(
            "/api/webhook/opsgenie",
            json=og_payload,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Verify incident was created
        assert data["incident_id"] > 0
        assert data["title"] == "High CPU utilization on app-server"
        assert data["severity"] == "SEV2"
        assert data["auto_classified"] is True
