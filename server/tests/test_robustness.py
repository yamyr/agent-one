"""Tests for server robustness & reliability hardening (branch 191-agent-loop-hardening).

Covers safe_get_choice helper, broadcaster connection limits, config timeout,
path traversal guards, concurrency locks, LLM timeout wrapping, safe_get_choice
adoption across all LLM callers, and broadened except clauses.
"""

import asyncio
import inspect
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm_utils import safe_get_choice


# ── 1. safe_get_choice ──


class TestSafeGetChoice(unittest.TestCase):
    def test_valid_response_returns_first_choice(self):
        response = MagicMock()
        choice = MagicMock()
        response.choices = [choice]
        result = safe_get_choice(response, "test")
        self.assertIs(result, choice)

    def test_multiple_choices_returns_first(self):
        response = MagicMock()
        c1, c2 = MagicMock(), MagicMock()
        response.choices = [c1, c2]
        self.assertIs(safe_get_choice(response), c1)

    def test_empty_choices_raises_runtime_error(self):
        response = MagicMock()
        response.choices = []
        with self.assertRaises(RuntimeError) as ctx:
            safe_get_choice(response, "rover")
        self.assertIn("empty choices", str(ctx.exception))
        self.assertIn("rover", str(ctx.exception))

    def test_none_choices_raises_runtime_error(self):
        response = MagicMock()
        response.choices = None
        with self.assertRaises(RuntimeError):
            safe_get_choice(response, "narrator")

    def test_no_choices_attr_raises_runtime_error(self):
        response = object()
        with self.assertRaises(RuntimeError):
            safe_get_choice(response, "station")

    def test_context_label_in_error_message(self):
        response = MagicMock()
        response.choices = []
        with self.assertRaises(RuntimeError) as ctx:
            safe_get_choice(response, "my-agent")
        self.assertIn("my-agent", str(ctx.exception))

    def test_no_context_label_still_works(self):
        response = MagicMock()
        response.choices = []
        with self.assertRaises(RuntimeError) as ctx:
            safe_get_choice(response)
        self.assertNotIn("()", str(ctx.exception))


# ── 2. Broadcaster connection limit & dead connection logging ──


class TestBroadcasterConnectionLimit(unittest.TestCase):
    def test_max_ws_connections_constant_exists(self):
        from app.broadcast import MAX_WS_CONNECTIONS

        self.assertEqual(MAX_WS_CONNECTIONS, 50)

    def test_connection_rejected_at_limit(self):
        from app.broadcast import Broadcaster, MAX_WS_CONNECTIONS

        b = Broadcaster()
        for _ in range(MAX_WS_CONNECTIONS):
            b._connections.append(MagicMock())

        ws = AsyncMock()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(b.connect(ws))
        finally:
            loop.close()

        ws.close.assert_called_once()
        call_kwargs = ws.close.call_args
        self.assertEqual(
            call_kwargs[1].get("code", call_kwargs[0][0] if call_kwargs[0] else None), 1013
        )
        self.assertEqual(len(b._connections), MAX_WS_CONNECTIONS)

    def test_connection_accepted_below_limit(self):
        from app.broadcast import Broadcaster

        b = Broadcaster()
        ws = AsyncMock()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(b.connect(ws))
        finally:
            loop.close()

        ws.accept.assert_called_once()
        self.assertIn(ws, b._connections)

    def test_dead_connection_logged_on_send(self):
        from app.broadcast import Broadcaster

        b = Broadcaster()
        dead_ws = AsyncMock()
        dead_ws.send_text.side_effect = Exception("connection lost")
        b._connections.append(dead_ws)

        loop = asyncio.new_event_loop()
        try:
            with patch("app.broadcast.logger") as mock_logger:
                loop.run_until_complete(b.send({"event": "test_event", "data": "test"}))
                mock_logger.warning.assert_any_call("Removing dead WebSocket connection")
        finally:
            loop.close()

        self.assertNotIn(dead_ws, b._connections)


# ── 3. Config llm_call_timeout ──


class TestConfigLlmCallTimeout(unittest.TestCase):
    def test_default_timeout_is_45(self):
        from app.config import Settings

        self.assertIn("llm_call_timeout", Settings.model_fields)

    def test_settings_instance_has_timeout(self):
        from app.config import settings

        self.assertIsInstance(settings.llm_call_timeout, float)
        self.assertGreater(settings.llm_call_timeout, 0)

    def test_default_value_is_45(self):
        from app.config import settings

        self.assertEqual(settings.llm_call_timeout, 45.0)


# ── 4. Path traversal in finetuning ──


class TestFinetuningPathTraversal(unittest.TestCase):
    def test_traversal_path_rejected(self):
        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        with self.assertRaises(ValueError) as ctx:
            mgr.upload_training_data("/etc/passwd")
        self.assertIn("Path traversal denied", str(ctx.exception))

    def test_relative_traversal_rejected(self):
        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        with self.assertRaises(ValueError) as ctx:
            mgr.upload_training_data("../../../etc/shadow")
        self.assertIn("Path traversal denied", str(ctx.exception))

    def test_path_validation_uses_normpath(self):
        from app.finetuning import FineTuningManager

        source = inspect.getsource(FineTuningManager.upload_training_data)
        self.assertIn("realpath", source)
        self.assertIn("startswith", source)


# ── 5. SPA fallback path traversal ──


class TestSPAFallbackPathTraversal(unittest.TestCase):
    def test_spa_fallback_has_path_traversal_guard(self):
        from app import main as main_module

        source = inspect.getsource(main_module)
        self.assertIn("_static_files", source)


# ── 6. Reset concurrency lock ──


class TestResetConcurrencyLock(unittest.TestCase):
    def test_reset_lock_exists(self):
        from app.main import _reset_lock

        self.assertIsInstance(_reset_lock, asyncio.Lock)

    def test_reset_simulation_uses_lock(self):
        source = inspect.getsource(
            __import__("app.main", fromlist=["reset_simulation"]).reset_simulation
        )
        self.assertIn("_reset_lock", source)

    def test_apply_preset_uses_lock(self):
        source = inspect.getsource(
            __import__("app.main", fromlist=["apply_preset_endpoint"]).apply_preset_endpoint
        )
        self.assertIn("_reset_lock", source)


# ── 7. World state lock ──


class TestWorldStateLock(unittest.TestCase):
    def test_world_lock_exists(self):
        from app.world import world_lock

        self.assertIsInstance(world_lock, asyncio.Lock)

    def test_world_lock_is_module_level(self):
        from app import world as world_module

        self.assertTrue(hasattr(world_module, "world_lock"))


# ── 8. Host station_startup uses wait_for ──


class TestHostTimeoutWrapping(unittest.TestCase):
    def test_station_startup_uses_wait_for(self):
        from app.host import Host

        source = inspect.getsource(Host.station_startup)
        self.assertIn("wait_for", source)
        self.assertIn("llm_call_timeout", source)


# ── 9. All LLM callers use safe_get_choice ──


class TestSafeGetChoiceAdoption(unittest.TestCase):
    def test_agent_imports_safe_get_choice(self):
        source = Path("app/agent.py").read_text()
        self.assertIn("from .llm_utils import safe_get_choice", source)

    def test_narrator_imports_safe_get_choice(self):
        source = Path("app/narrator.py").read_text()
        self.assertIn("from .llm_utils import safe_get_choice", source)

    def test_station_imports_safe_get_choice(self):
        source = Path("app/station.py").read_text()
        self.assertIn("from .llm_utils import safe_get_choice", source)

    def test_voice_imports_safe_get_choice(self):
        source = Path("app/voice.py").read_text()
        self.assertIn("from .llm_utils import safe_get_choice", source)

    def test_no_raw_choices_0_in_agent(self):
        source = Path("app/agent.py").read_text()
        import re

        matches = re.findall(r"\.choices\[0\]", source)
        self.assertEqual(len(matches), 0, f"Found {len(matches)} raw .choices[0] in agent.py")

    def test_no_raw_choices_0_in_station(self):
        source = Path("app/station.py").read_text()
        import re

        matches = re.findall(r"\.choices\[0\]", source)
        self.assertEqual(len(matches), 0, f"Found {len(matches)} raw .choices[0] in station.py")

    def test_no_raw_choices_0_in_voice(self):
        source = Path("app/voice.py").read_text()
        import re

        matches = re.findall(r"\.choices\[0\]", source)
        self.assertEqual(len(matches), 0, f"Found {len(matches)} raw .choices[0] in voice.py")

    def test_narrator_non_streaming_uses_safe_get_choice(self):
        source = Path("app/narrator.py").read_text()
        self.assertIn("safe_get_choice(response", source)


# ── 10. Broadened except clauses ──


class TestBroadenedExceptClauses(unittest.TestCase):
    def test_agent_except_clauses_include_runtime_error(self):
        from app.agent import (
            DroneAgent,
            HaulerAgent,
            HuggingFaceDroneAgent,
            HuggingFaceRoverReasoner,
            MistralRoverReasoner,
        )

        for cls in [MistralRoverReasoner, HaulerAgent, DroneAgent]:
            source = inspect.getsource(cls.run_turn)
            self.assertIn(
                "RuntimeError",
                source,
                f"{cls.__name__}.run_turn missing RuntimeError in except",
            )

        for cls in [HuggingFaceRoverReasoner, HuggingFaceDroneAgent]:
            source = inspect.getsource(cls.run_turn)
            self.assertIn(
                "RuntimeError",
                source,
                f"{cls.__name__}.run_turn missing RuntimeError in except",
            )

    def test_agent_except_clauses_include_asyncio_timeout(self):
        from app.agent import (
            DroneAgent,
            HaulerAgent,
            HuggingFaceDroneAgent,
            HuggingFaceRoverReasoner,
            MistralRoverReasoner,
        )

        for cls in [
            MistralRoverReasoner,
            HaulerAgent,
            DroneAgent,
            HuggingFaceRoverReasoner,
            HuggingFaceDroneAgent,
        ]:
            source = inspect.getsource(cls.run_turn)
            self.assertIn(
                "asyncio.TimeoutError",
                source,
                f"{cls.__name__}.run_turn missing asyncio.TimeoutError in except",
            )

    def test_agent_except_clauses_include_json_decode_error(self):
        from app.agent import (
            DroneAgent,
            HaulerAgent,
            HuggingFaceDroneAgent,
            HuggingFaceRoverReasoner,
            MistralRoverReasoner,
        )

        for cls in [
            MistralRoverReasoner,
            HaulerAgent,
            DroneAgent,
            HuggingFaceRoverReasoner,
            HuggingFaceDroneAgent,
        ]:
            source = inspect.getsource(cls.run_turn)
            self.assertIn(
                "JSONDecodeError",
                source,
                f"{cls.__name__}.run_turn missing json.JSONDecodeError in except",
            )


# ── 11. llm_utils module structure ──


class TestLlmUtilsModule(unittest.TestCase):
    def test_module_importable(self):
        import app.llm_utils

        self.assertTrue(hasattr(app.llm_utils, "safe_get_choice"))

    def test_function_has_docstring(self):
        self.assertIsNotNone(safe_get_choice.__doc__)
        self.assertIn("choices", safe_get_choice.__doc__)

    def test_function_signature(self):
        sig = inspect.signature(safe_get_choice)
        params = list(sig.parameters.keys())
        self.assertEqual(params, ["response", "context"])


if __name__ == "__main__":
    unittest.main()
