# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

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
