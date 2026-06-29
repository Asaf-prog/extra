"""HTTP routes via TestClient — stub engine + in-memory repo, no DB or LLM."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_engine.engine.engine import Engine
from agent_engine.engine.types import RunResult
from agent_engine.runtime.hooks.models import RunContext
from agent_engine.runtime.streaming import RunStreamEvent
from agent_manager.api.routes import router
from agent_manager.application import ConversationService
from agent_manager.infrastructure.persistence.memory_repository import MemoryRepository
from tests.agent_manager.conftest import RecordingEngine


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.state.service = ConversationService(RecordingEngine(), MemoryRepository())
    app.include_router(router)
    return TestClient(app)


def test_create_send_history_round_trip(client: TestClient) -> None:
    cid = client.post("/conversations").json()["conversation_id"]

    sent = client.post(f"/conversations/{cid}/messages", json={"message": "hello"})
    assert sent.status_code == 200
    assert sent.json()["answer"] == "answer:hello"

    msgs = client.get(f"/conversations/{cid}/messages").json()
    assert [(m["role"], m["content"]) for m in msgs] == [
        ("user", "hello"),
        ("assistant", "answer:hello"),
    ]


def test_unknown_conversation_returns_404(client: TestClient) -> None:
    assert client.get("/conversations/nope/messages").status_code == 404
    assert client.post("/conversations/nope/messages", json={"message": "x"}).status_code == 404


class _SubAgentEngine(Engine):
    """Stub that mimics a parent orchestrator routing to a sub-agent.

    Mirrors what the real widget_sub_agent_demo config produces: the route
    visits the root orchestrator and then a sub-agent path. Lets us assert the
    real conversation API surfaces sub-agent participation without an LLM.
    """

    async def build(self, _spec: object) -> None: ...

    async def run(self, message: str, *, context: RunContext | None = None) -> RunResult:
        return RunResult(
            system_name="Widget Sub-Agent Demo",
            visited=["concierge_router", "concierge_router/tags_agent"],
            answer="The available document tags are: finance, legal, hr.",
        )

    async def stream(
        self, message: str, *, context: RunContext | None = None
    ) -> AsyncIterator[RunStreamEvent]:
        yield RunStreamEvent(type="final", content="unused")


def test_send_surfaces_sub_agent_in_visited_without_mocking() -> None:
    """End-to-end through the real routes + service: the response exposes the
    sub-agent routing path (the evidence the demo page renders)."""
    app = FastAPI()
    app.state.service = ConversationService(_SubAgentEngine(), MemoryRepository())
    app.include_router(router)
    client = TestClient(app)

    cid = client.post("/conversations").json()["conversation_id"]
    body = client.post(f"/conversations/{cid}/messages", json={"message": "tags?"}).json()

    assert body["visited"] == ["concierge_router", "concierge_router/tags_agent"]
    assert any("/" in hop for hop in body["visited"]), "expected a sub-agent hop"
    assert "finance" in body["answer"]


def test_create_accepts_stable_session_and_send_accepts_user(client: TestClient) -> None:
    created = client.post("/conversations", json={"session_id": "sess-1", "user_id": "u1"}).json()
    assert created["conversation_id"] == "sess-1"
    assert created["session_id"] == "sess-1"

    sent = client.post("/conversations/sess-1/messages", json={"message": "hello", "user_id": "u1"})

    assert sent.status_code == 200
