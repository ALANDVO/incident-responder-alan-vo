# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

incident-triage-baseline

## Roadmap

### incident-triage-baseline — Incident triage, blast radius analysis, and comms generation

Status: done

Acceptance:
- Classify incident severity across SEV1-SEV4 with confidence scoring and containment playbooks
- Compute blast radius affected services, dependencies, and data impact
- Generate multi-channel communication drafts for Status Page, Slack, and email templates
- Full FastAPI backend with persistent SQLite storage and JWT/OIDC authentication routes
- React + TypeScript frontend dashboard with responsive workflow interfaces

Implementation: `backend/app/main.py`, `backend/app/api/incidents.py`, `backend/app/services/incident.py`, `frontend/src/App.tsx`, `frontend/src/pages/IncidentDetailPage.tsx`

Tests: `backend/tests/test_auth.py`, `backend/tests/test_incidents.py`, `frontend/src/App.test.tsx`

### keycloak-oidc-production-broker — Keycloak OIDC and SAML identity brokering integration

Status: planned

Acceptance:
- Validate Keycloak authorization code flow with PKCE
- Sync upstream SAML user groups and roles directly

### real-time-pagerduty-webhook — Real-time PagerDuty and OpsGenie webhook ingestion

Status: planned

Acceptance:
- Parse automated incoming alerts into incident timeline
- Automatically trigger SEV classification on high-urgency alarms

