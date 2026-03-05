"""Tests for human-in-the-loop confirmation system."""

import asyncio
import uuid


from app.host import Host, CONFIRM_DEFAULT_TIMEOUT
from app.narrator import Narrator


# ── Helpers ──


def _make_host():
    """Create a Host with a no-op narrator for testing."""
    narrator = Narrator(broadcast_fn=lambda msg: asyncio.coroutine(lambda: None)())
    return Host(narrator=narrator)


# ── Phase 2: Host confirmation infrastructure ──


class TestHostConfirmation:
    """Tests for Host._pending_confirms management."""

    def test_confirm_default_timeout_constant(self):
        assert CONFIRM_DEFAULT_TIMEOUT == 30

    def test_create_confirm_returns_uuid(self):
        host = _make_host()
        request_id = host.create_confirm("rover-mistral", "Cross hazard?", 30)
        # Should be a valid UUID string
        uuid.UUID(request_id)  # Raises if invalid

    def test_create_confirm_stores_entry(self):
        host = _make_host()
        request_id = host.create_confirm("rover-mistral", "Cross hazard?", 30)
        entry = host.get_pending_confirm(request_id)
        assert entry is not None
        assert entry["agent_id"] == "rover-mistral"
        assert entry["question"] == "Cross hazard?"
        assert entry["timeout"] == 30
        assert entry["response"] is None
        assert isinstance(entry["event"], asyncio.Event)

    def test_resolve_confirm_sets_response_and_event(self):
        host = _make_host()
        request_id = host.create_confirm("rover-mistral", "Cross hazard?", 30)
        result = host.resolve_confirm(request_id, True)
        assert result is True
        entry = host.get_pending_confirm(request_id)
        assert entry["response"] is True
        assert entry["event"].is_set()

    def test_resolve_confirm_deny(self):
        host = _make_host()
        request_id = host.create_confirm("rover-mistral", "Cross hazard?", 30)
        result = host.resolve_confirm(request_id, False)
        assert result is True
        entry = host.get_pending_confirm(request_id)
        assert entry["response"] is False
        assert entry["event"].is_set()

    def test_resolve_nonexistent_returns_false(self):
        host = _make_host()
        result = host.resolve_confirm("nonexistent-id", True)
        assert result is False

    def test_get_agent_pending_confirm(self):
        host = _make_host()
        host.create_confirm("rover-mistral", "Cross hazard?", 30)
        entry = host.get_agent_pending_confirm("rover-mistral")
        assert entry is not None
        assert entry["agent_id"] == "rover-mistral"
        # Non-existent agent returns None
        assert host.get_agent_pending_confirm("drone-mistral") is None

    def test_cleanup_confirm_removes_entry(self):
        host = _make_host()
        request_id = host.create_confirm("rover-mistral", "Cross hazard?", 30)
        host.cleanup_confirm(request_id)
        assert host.get_pending_confirm(request_id) is None
        assert host.get_agent_pending_confirm("rover-mistral") is None

    def test_one_per_agent_limit(self):
        """Only one pending confirmation per agent. Creating a new one replaces the old."""
        host = _make_host()
        id1 = host.create_confirm("rover-mistral", "First question?", 30)
        id2 = host.create_confirm("rover-mistral", "Second question?", 30)
        # Old one should be cleaned up
        assert host.get_pending_confirm(id1) is None
        entry = host.get_pending_confirm(id2)
        assert entry is not None
        assert entry["question"] == "Second question?"


# ── Phase 3 (US1): Request Confirm Tool ──


class TestRequestConfirmTool:
    """Tests for REQUEST_CONFIRM_TOOL schema and ROVER_TOOLS integration."""

    def test_tool_schema_valid(self):
        from app.agent import REQUEST_CONFIRM_TOOL

        func = REQUEST_CONFIRM_TOOL["function"]
        assert func["name"] == "request_confirm"
        params = func["parameters"]["properties"]
        assert "question" in params
        assert params["question"]["type"] == "string"
        assert "timeout" in params
        assert params["timeout"]["type"] == "integer"
        assert func["parameters"]["required"] == ["question"]

    def test_tool_in_rover_tools(self):
        from app.agent import ROVER_TOOLS

        names = [t["function"]["name"] for t in ROVER_TOOLS]
        assert "request_confirm" in names

    def test_tool_has_description(self):
        from app.agent import REQUEST_CONFIRM_TOOL

        desc = REQUEST_CONFIRM_TOOL["function"]["description"]
        assert "confirmation" in desc.lower() or "confirm" in desc.lower()
        assert "high-risk" in desc.lower() or "storm" in desc.lower()


# ── Phase 4 (US2): Confirm Endpoint ──


class TestConfirmEndpoint:
    """Tests for POST /api/confirm endpoint."""

    def test_valid_confirm_returns_ok(self):
        from fastapi.testclient import TestClient
        from app.main import app, host

        request_id = host.create_confirm("rover-mistral", "Cross hazard?", 30)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/confirm", json={"request_id": request_id, "confirmed": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["confirmed"] is True
        # Cleanup
        host.cleanup_confirm(request_id)

    def test_valid_deny_returns_ok(self):
        from fastapi.testclient import TestClient
        from app.main import app, host

        request_id = host.create_confirm("rover-mistral", "Cross hazard?", 30)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/confirm", json={"request_id": request_id, "confirmed": False})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["confirmed"] is False
        host.cleanup_confirm(request_id)

    def test_not_found_request_id(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/confirm", json={"request_id": "nonexistent", "confirmed": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "error" in data

    def test_missing_fields_returns_error(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app, raise_server_exceptions=False)
        # Missing confirmed field
        resp = client.post("/api/confirm", json={"request_id": "some-id"})
        assert resp.status_code in (200, 422)
        # Missing request_id
        resp2 = client.post("/api/confirm", json={"confirmed": True})
        assert resp2.status_code in (200, 422)


# ── Phase 6 (US4): Rover Confirm Prompt ──


class TestRoverConfirmPrompt:
    """Tests for HUMAN CONFIRMATION section in rover system prompt."""

    def _get_context(self):
        """Build a rover context to inspect the system prompt."""
        from app.agent import MistralRoverReasoner
        from app.world import World

        world = World()
        reasoner = MistralRoverReasoner(agent_id="rover-mistral", world=world)
        return reasoner._build_context()

    def test_prompt_contains_human_confirmation_section(self):
        ctx = self._get_context()
        assert "HUMAN CONFIRMATION" in ctx

    def test_prompt_mentions_storm(self):
        ctx = self._get_context()
        lower = ctx.lower()
        assert "storm" in lower

    def test_prompt_mentions_hazard(self):
        ctx = self._get_context()
        lower = ctx.lower()
        assert "hazard" in lower or "geyser" in lower

    def test_prompt_discourages_overuse(self):
        ctx = self._get_context()
        lower = ctx.lower()
        assert "do not" in lower or "don't" in lower or "routine" in lower
