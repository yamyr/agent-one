"""Training data collector — records LLM interactions as JSONL for fine-tuning."""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from .config import settings

logger = logging.getLogger(__name__)


class TrainingDataCollector:
    """Singleton that appends LLM interactions to JSONL files for Mistral fine-tuning.

    Thread-safe via ``threading.Lock`` (agents run in ``asyncio.to_thread``).
    """

    def __init__(self):
        self._enabled = settings.training_data_enabled
        self._data_dir = Path(settings.training_data_dir)
        self._lock = threading.Lock()
        self._files: dict[str, Path] = {}
        self._session_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # -- public API --

    def record_agent_interaction(
        self,
        agent_id: str,
        agent_type: str,
        messages: list,
        tools: list,
        response,
    ) -> None:
        """Record an agent LLM call (with tool use) as a JSONL sample."""
        if not self._enabled:
            return
        try:
            sample = self._build_agent_sample(messages, response)
            self._append(agent_type, sample)
        except Exception:
            logger.exception("Failed to record agent interaction for %s", agent_id)

    def record_narration_interaction(
        self,
        messages: list,
        response_text: str,
    ) -> None:
        """Record a narration LLM call (no tools) as a JSONL sample."""
        if not self._enabled:
            return
        try:
            sample = self._build_narration_sample(messages, response_text)
            self._append("narration", sample)
        except Exception:
            logger.exception("Failed to record narration interaction")

    # -- internal helpers --

    def _build_agent_sample(self, messages: list, response) -> dict:
        """Convert an agent LLM call into the Mistral fine-tuning JSONL format."""
        out_messages: list[dict] = []

        # Copy input messages (system + user)
        for msg in messages:
            out_messages.append({"role": msg["role"], "content": msg["content"]})

        # Assistant response
        choice = response.choices[0]
        assistant_msg: dict = {
            "role": "assistant",
            "content": choice.message.content or "",
        }

        if choice.message.tool_calls:
            tool_calls_out = []
            for tc in choice.message.tool_calls:
                args = tc.function.arguments
                if not isinstance(args, str):
                    args = json.dumps(args)
                tool_calls_out.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": args,
                        },
                    }
                )
            assistant_msg["tool_calls"] = tool_calls_out

        out_messages.append(assistant_msg)

        # Append tool result placeholders for each tool call
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                out_messages.append(
                    {
                        "role": "tool",
                        "content": "ok",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                    }
                )

        return {"messages": out_messages}

    def _build_narration_sample(self, messages: list, response_text: str) -> dict:
        """Convert a narration LLM call into JSONL format (no tools)."""
        out_messages: list[dict] = []
        for msg in messages:
            out_messages.append({"role": msg["role"], "content": msg["content"]})
        out_messages.append({"role": "assistant", "content": response_text})
        return {"messages": out_messages}

    def _get_file_path(self, agent_type: str) -> Path:
        """Return (and cache) the JSONL file path for a given agent type."""
        if agent_type not in self._files:
            filename = f"{agent_type}_training_{self._session_ts}.jsonl"
            self._files[agent_type] = self._data_dir / filename
        return self._files[agent_type]

    def _append(self, agent_type: str, sample: dict) -> None:
        """Thread-safe append of a JSON line to the appropriate file."""
        path = self._get_file_path(agent_type)
        line = json.dumps(sample, ensure_ascii=False) + "\n"
        with self._lock:
            os.makedirs(path.parent, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)


collector = TrainingDataCollector()
