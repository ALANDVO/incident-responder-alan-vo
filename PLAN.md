# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

deterministic-classification-engine

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

### deterministic-classification-engine — Rule-based severity classification and containment playbooks

Status: done

Acceptance:
- Classify incident severity (SEV1-SEV4) from incident text using keyword and pattern matching with confidence scoring
- SEV1 indicators take precedence over lower severity levels
- Generate incident-specific containment playbooks per severity level
- Extract affected infrastructure services from incident text for blast-radius analysis
- Generate multi-channel comms templates (Status Page, Slack, Email) without leaking instruction text
- Generate deterministic postmortem skeleton with service extraction and severity-based action items
- Postmortem timeline uses fixed reference time for deterministic output; optional detected_at parameter for custom timestamps

Implementation: `backend/app/services/classifier.py`, `backend/app/services/incident.py`

Tests: `backend/tests/test_classifier.py`, `backend/tests/test_incidents.py`

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

