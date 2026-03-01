"""Training data collector — records LLM interactions as JSONL for fine-tuning."""

import json
import logging
import os
import threading
from datetime import datetime, timezone

from .config import settings

logger = logging.getLogger(__name__)


class TrainingDataCollector:
    """Thread-safe collector that writes LLM interactions to JSONL files."""

    def __init__(self):
        self._enabled = settings.training_data_enabled
        self._data_dir = settings.training_data_dir
        self._lock = threading.Lock()
        self._session_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._counts: dict[str, int] = {}

    def _ensure_dir(self):
        os.makedirs(self._data_dir, exist_ok=True)

    def _file_path(self, agent_type: str) -> str:
        return os.path.join(self._data_dir, f"{agent_type}_training_{self._session_ts}.jsonl")

    def record_agent_interaction(
        self,
        agent_id: str,
        agent_type: str,
        messages: list[dict],
        tools: list[dict],
        response,
    ):
        """Record an agent LLM call with tool_calls to JSONL."""
        if not self._enabled:
            return
        try:
            choice = response.choices[0]
            assistant_msg: dict = {"role": "assistant"}
            if choice.message.content:
                assistant_msg["content"] = choice.message.content

            if choice.message.tool_calls:
                tool_calls_data = []
                for tc in choice.message.tool_calls:
                    args = tc.function.arguments
                    if isinstance(args, str):
                        args = json.loads(args)
                    tool_calls_data.append(
                        {
                            "id": getattr(tc, "id", "call_0"),
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": json.dumps(args)},
                        }
                    )
                assistant_msg["tool_calls"] = tool_calls_data

            training_messages = list(messages) + [assistant_msg]

            # Add tool result placeholders after assistant tool_calls
            if choice.message.tool_calls:
                for tc_data in tool_calls_data:
                    training_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_data["id"],
                            "content": "{}",
                        }
                    )

            record = {"messages": training_messages}
            self._write_record(agent_type, record)
        except Exception:
            logger.exception("Failed to record agent interaction for %s", agent_id)

    def record_narration_interaction(self, messages: list[dict], response_text: str):
        """Record a narrator LLM call (no tools) to JSONL."""
        if not self._enabled:
            return
        try:
            training_messages = list(messages) + [{"role": "assistant", "content": response_text}]
            record = {"messages": training_messages}
            self._write_record("narration", record)
        except Exception:
            logger.exception("Failed to record narration interaction")

    def _write_record(self, agent_type: str, record: dict):
        with self._lock:
            self._ensure_dir()
            path = self._file_path(agent_type)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._counts[agent_type] = self._counts.get(agent_type, 0) + 1

    def get_stats(self) -> dict:
        """Return dict with file sizes and sample counts."""
        stats: dict = {}
        with self._lock:
            if not os.path.isdir(self._data_dir):
                return stats
            for fname in os.listdir(self._data_dir):
                if fname.endswith(".jsonl"):
                    fpath = os.path.join(self._data_dir, fname)
                    size = os.path.getsize(fpath)
                    samples = 0
                    with open(fpath, encoding="utf-8") as f:
                        for _ in f:
                            samples += 1
                    stats[fname] = {"size_bytes": size, "samples": samples}
        return stats


collector = TrainingDataCollector()
