"""Pytest fixtures for the incident-responder backend.

The backend builds its SQLAlchemy engine from ``settings.database_url`` at import
time. To keep tests hermetic and free of any network/LLM dependency, we pin a
throwaway environment *before* importing the app, then replace the module-level
engine/session factory with a fresh per-test SQLite database. No real credential
or provider call is ever made: the incident workflows are exercised with the
deterministic ``use_llm=False`` path.
"""
import os
import tempfile
import uuid
import pathlib

_tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="ir-test-"))
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_tmpdir / 'test.db'}")
os.environ.setdefault("JWT_SECRET", "pytest-jwt-secret-not-real")
os.environ.setdefault("LLM_API_KEY", "")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("OIDC_ENABLED", "false")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.main import app  # noqa: E402  (import after env is pinned)
from app.core.database import Base  # noqa: E402

import app.core.database as _dbmod  # noqa: E402


@pytest.fixture
async def db():
    """Replace the module-level engine with a fresh isolated SQLite DB per test."""
    db_path = _tmpdir / f"{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    _original_engine = _dbmod.engine
    _original_sessions = _dbmod.async_session_maker
    _dbmod.engine = engine
    _dbmod.async_session_maker = session_maker

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield {"engine": engine, "session_maker": session_maker}
    finally:
        await engine.dispose()
        _dbmod.engine = _original_engine
        _dbmod.async_session_maker = _original_sessions


@pytest.fixture
async def client(db):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http:
        yield http


@pytest.fixture
async def auth_token(client):
    """Factory: register a user of the given role and return a bearer token."""

    async def _make(
        email="user@example.com", password="Password123!", role="operator"
    ) -> str:
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Tester",
                "role": role,
            },
        )
        assert resp.status_code == 201, resp.text
        resp = await client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    return _make


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}