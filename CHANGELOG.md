# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-10-17

### Added
- Deterministic classification engine (`backend/app/services/classifier.py`): rule-based SEV1–SEV4 severity classification with confidence scoring, keyword/regex pattern matching ordered by impact level, and severity-precedence resolution.
- Severity-specific containment playbooks generated from classification results (escalation for SEV1, mitigation for SEV2, monitoring for SEV3/SEV4).
- Infrastructure service-name and cloud-region extraction from incident text for deterministic blast-radius analysis.
- Multi-channel comms template generation (Status Page, Slack, Email) that produces real templates from incident data instead of leaking LLM instruction text into output.
- Deterministic postmortem skeleton generator with timeline reconstruction, root-cause hypothesis, severity-based action items, and [TO BE VERIFIED] markers for unsupported claims.

### Fixed
- Deterministic triage fallback no longer returns a hardcoded SEV3/0.5 confidence for every incident; severity is now derived from incident content.
- Comms fallback no longer leaks internal LLM instruction text (e.g., "Write the initial status page update…") into user-facing template output.
- `llm_provider`/`llm_model` fields on TriageResult, BlastAnalysis, CommsTemplate, and Postmortem now correctly report "fallback"/"none" when the deterministic path is used.
- `matched_severity` in the classifier now correctly resolves to the highest severity level with matching indicators, not the last one.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## [1.0.0] - 2026-10-12

### Added
- Incident response core engine with deterministic severity triage (SEV1-SEV4).
- Blast radius analysis mapping affected services, user cohorts, data impact, and dependency chains.
- Multi-channel communications generator for Status Page, Slack, and stakeholder emails.
- FastAPI backend with SQLite persistence, SQLAlchemy async sessions, and role-based access control.
- Modern React + TypeScript + Vite frontend dashboard with real-time status metrics and workflows.
- Multi-provider LLM client supporting OpenAI, Anthropic Claude, Google Gemini, and local Ollama endpoints.
- Docker containerization and compose topology with Keycloak identity broker integration.
- Full automated test suite for backend services, API routes, and frontend components.