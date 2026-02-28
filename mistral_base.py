"""Base agent class that speaks the Snowball protocol over stdio.

Wraps the Mistral API with tool use, streaming, and the full
AgentEvent/AgentCommand JSON protocol. Subclass and override
system_prompt() to build pipeline agents.

Usage:
    from snowball.agents import BaseAgent

    class MyAgent(BaseAgent):
        def __init__(self):
            super().__init__("myns/myagent", "My Agent", "Does things")

        def system_prompt(self):
            return "You are a helpful agent."

    if __name__ == "__main__":
        MyAgent().run()
"""

import json
import logging
import os
import subprocess
import sys
import traceback

from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.models.textchunk import TextChunk
from mistralai.models.thinkchunk import ThinkChunk

load_dotenv()

log = logging.getLogger(__name__)


def _setup_logging(agent_id):
    """Configure file logging, return log path."""
    safe_name = agent_id.replace("/", "_")
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{safe_name}.log")
    logging.basicConfig(
        filename=log_file,
        filemode="w",
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return log_file


class BaseAgent:
    """Base class for Snowball-protocol agents backed by Mistral API."""

    def __init__(self, agent_id, name, description, model="devstral-small-latest", tools=None):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.model = model
        self.messages = []
        self._cancelled = False
        self._tools = {}
        self._tool_schemas = []
        self._client = None
        self._log_file = None

        # Register built-in tools
        self._register_builtins()

        # Register additional tools
        if tools:
            for t in tools:
                self.register_tool(t["name"], t["fn"], t["description"], t["parameters"])

    # ── Protocol ──────────────────────────────────────────────

    def emit(self, event):
        """Write one AgentEvent JSON line to stdout."""
        print(json.dumps(event), flush=True)

    def emit_text_message(self, text):
        """Emit a complete text message (MessageStart → PartDelta → PartEnd → MessageEnd)."""
        self.emit({"MessageStart": {"role": "Agent"}})
        self.emit({"PartDelta": {"part_index": 0, "kind": "Text", "delta": text}})
        self.emit({"PartEnd": {"part_index": 0, "kind": "Text", "full_content": text}})
        self.emit("MessageEnd")

    def emit_status(self, text, key="status"):
        """Emit a StatusUpdate event."""
        self.emit({"StatusUpdate": {"key": key, "text": text}})

    def emit_error(self, message):
        """Emit an Error event."""
        self.emit({"Error": {"message": message}})

    def read_command(self):
        """Read one AgentCommand JSON line from stdin. Returns None on EOF."""
        line = sys.stdin.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            log.warning("Bad JSON from stdin: %s", line)
            return None

    def startup(self):
        """Emit the startup sequence: AgentCard → StateChanged(Completed)."""
        self.emit({"AgentCard": {
            "humanReadableId": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": "0.1.0",
            "capabilities": {"streaming": True},
            "skills": [
                {"id": "chat", "name": "Chat", "description": "General chat", "tags": []},
            ],
        }})
        self.emit({"StateChanged": {"state": "Completed", "reason": None}})
        if self._log_file:
            self.emit({"Metadata": {"key": "log_file", "value": self._log_file}})

    # ── Tool framework ────────────────────────────────────────

    def register_tool(self, name, fn, description, parameters):
        """Register a tool function with its JSON schema."""
        self._tools[name] = fn
        self._tool_schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        })

    def execute_tool(self, call_id, name, args_json):
        """Run a tool, emitting ToolStart/ToolEnd. Returns the output string."""
        args = json.loads(args_json) if isinstance(args_json, str) else args_json
        self.emit({"ToolStart": {"call_id": call_id, "tool_name": name, "args": args}})

        fn = self._tools.get(name)
        if not fn:
            output = f"Error: unknown tool '{name}'"
            self.emit({"ToolEnd": {"call_id": call_id, "output": output, "is_error": True}})
            return output

        try:
            output = fn(**args)
            if not isinstance(output, str):
                output = json.dumps(output)
            is_error = False
        except Exception:
            output = traceback.format_exc()
            is_error = True

        self.emit({"ToolEnd": {"call_id": call_id, "output": output, "is_error": is_error}})
        return output

    def _register_builtins(self):
        """Register the built-in tools."""
        self.register_tool(
            "read_file", tool_read_file,
            "Read a file from disk and return its contents.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path (absolute or relative)"},
                },
                "required": ["path"],
            },
        )
        self.register_tool(
            "write_file", tool_write_file,
            "Write content to a file, creating directories as needed.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path (absolute or relative)"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        )
        self.register_tool(
            "bash", tool_bash,
            "Execute a shell command and return stdout+stderr.",
            {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                },
                "required": ["command"],
            },
        )
        self.register_tool(
            "grep", tool_grep,
            "Search files for a pattern using ripgrep (rg) or grep.",
            {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "Directory or file to search in", "default": "."},
                    "include": {"type": "string", "description": "Glob pattern to filter files (e.g. '*.py')"},
                },
                "required": ["pattern"],
            },
        )

    # ── Mistral API ───────────────────────────────────────────

    def _get_client(self):
        if self._client is None:
            api_key = os.environ.get("MISTRAL_API_KEY")
            if not api_key:
                raise RuntimeError("MISTRAL_API_KEY environment variable not set")
            self._client = Mistral(api_key=api_key)
        return self._client

    def system_prompt(self):
        """Override in subclass to provide a system prompt."""
        return "You are a helpful coding agent. Use the tools available to complete tasks."

    def _build_messages(self):
        """Build the full message list with system prompt prepended."""
        return [{"role": "system", "content": self.system_prompt()}] + self.messages

    def chat_stream(self):
        """Call Mistral streaming API. Yields chunks, returns full response at end.

        Emits PartDelta events for text content as it streams.
        Returns the complete response object (last chunk with finish_reason).
        """
        client = self._get_client()
        messages = self._build_messages()
        tools = self._tool_schemas if self._tool_schemas else None

        accumulated_text = ""
        accumulated_thinking = ""
        accumulated_tool_calls = {}

        with client.chat.stream(
            model=self.model,
            messages=messages,
            tools=tools,
        ) as stream:
            for event in stream:
                chunk = event.data
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                if delta.content:
                    log.info("provider chunk: content=%r", delta.content)
                if delta.tool_calls:
                    log.info("provider chunk: tool_calls=%r", delta.tool_calls)
                if delta.content:
                    if isinstance(delta.content, str):
                        accumulated_text += delta.content
                        self.emit({"PartDelta": {"part_index": 0, "kind": "Text", "delta": delta.content}})
                    elif isinstance(delta.content, list):
                        for chunk_item in delta.content:
                            if isinstance(chunk_item, TextChunk):
                                accumulated_text += chunk_item.text
                                self.emit({"PartDelta": {"part_index": 0, "kind": "Text", "delta": chunk_item.text}})
                            elif isinstance(chunk_item, ThinkChunk):
                                for t in chunk_item.thinking:
                                    if isinstance(t, TextChunk):
                                        accumulated_thinking += t.text
                                        self.emit({"PartDelta": {"part_index": 1, "kind": "Thinking", "delta": t.text}})

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index if tc.index is not None else 0
                        if idx not in accumulated_tool_calls:
                            accumulated_tool_calls[idx] = {
                                "id": tc.id or "",
                                "name": tc.function.name or "",
                                "arguments": tc.function.arguments or "",
                            }
                        else:
                            entry = accumulated_tool_calls[idx]
                            if tc.id:
                                entry["id"] = tc.id
                            if tc.function.name:
                                entry["name"] += tc.function.name
                            if tc.function.arguments:
                                entry["arguments"] += tc.function.arguments

        # Build result
        tool_calls = []
        if accumulated_tool_calls:
            for idx in sorted(accumulated_tool_calls.keys()):
                tc = accumulated_tool_calls[idx]
                tool_calls.append(tc)

        return accumulated_text, accumulated_thinking, tool_calls

    def run_turn(self, user_message):
        """Run a full agent turn: chat → tool calls → chat → ... → done.

        Emits the full message lifecycle events.
        """
        self._cancelled = False
        self.messages.append({"role": "user", "content": user_message})
        self.emit({"StateChanged": {"state": "Working", "reason": None}})

        self._agent_loop()

        self.emit({"StateChanged": {"state": "Completed", "reason": None}})

    def _agent_loop(self):
        """Inner loop: chat, handle tool calls, repeat until done or cancelled."""
        while not self._cancelled:
            self.emit({"MessageStart": {"role": "Agent"}})

            try:
                text, thinking, tool_calls = self.chat_stream()
            except Exception:
                tb = traceback.format_exc()
                log.error("Chat API error: %s", tb)
                self.emit_error(f"Mistral API error: {tb}")
                self.emit("MessageEnd")
                return

            self.emit_status("")

            # Finalize thinking part (part_index=1, emitted before text)
            if thinking:
                self.emit({"PartEnd": {"part_index": 1, "kind": "Thinking", "full_content": thinking}})

            # Finalize text part
            if text:
                self.emit({"PartEnd": {"part_index": 0, "kind": "Text", "full_content": text}})

            # If no tool calls, we're done
            if not tool_calls:
                self.emit("MessageEnd")
                # Record assistant message in history
                self.messages.append({"role": "assistant", "content": text})
                return

            self.emit("MessageEnd")

            # Record assistant message with tool calls in history
            assistant_msg = {"role": "assistant", "content": text or None, "tool_calls": []}
            for tc in tool_calls:
                assistant_msg["tool_calls"].append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    },
                })
            self.messages.append(assistant_msg)

            # Execute tool calls
            for tc in tool_calls:
                if self._cancelled:
                    break
                output = self.execute_tool(tc["id"], tc["name"], tc["arguments"])
                self.messages.append({
                    "role": "tool",
                    "name": tc["name"],
                    "content": output,
                    "tool_call_id": tc["id"],
                })

            # Loop back for next chat turn

    # ── Command dispatch ──────────────────────────────────────

    def handle_send(self, message):
        """Handle a Send command."""
        self.run_turn(message)

    def handle_steer(self, message):
        """Handle a Steer command — inject as system message."""
        self.messages.append({"role": "system", "content": message})
        log.info("Steer: %s", message)

    def handle_cancel(self):
        """Handle a Cancel command."""
        self._cancelled = True
        self.emit({"StateChanged": {"state": "Canceled", "reason": "User cancelled"}})
        log.info("Cancelled")

    def handle_set_model(self, provider, model_id):
        """Handle a SetModel command."""
        self.model = model_id
        log.info("Model changed to %s/%s", provider, model_id)

    # ── Main loop ─────────────────────────────────────────────

    def run(self):
        """Main entry point. Reads commands from stdin in a loop."""
        self._log_file = _setup_logging(self.agent_id)
        log.info("Agent %s starting (pid=%d)", self.agent_id, os.getpid())

        self.startup()

        while True:
            cmd = self.read_command()
            if cmd is None:
                break

            if isinstance(cmd, str):
                if cmd == "Cancel":
                    self.handle_cancel()
                elif cmd == "GetState":
                    self.emit({"CommandResponse": {
                        "id": "getstate",
                        "command": "GetState",
                        "success": True,
                        "data": {"messages": len(self.messages), "model": self.model},
                        "error": None,
                    }})
                elif cmd == "Compact":
                    log.info("Compact requested (not implemented)")
                continue

            if isinstance(cmd, dict):
                if "Send" in cmd:
                    self.handle_send(cmd["Send"]["message"])
                elif "Steer" in cmd:
                    self.handle_steer(cmd["Steer"]["message"])
                elif "Cancel" in cmd:
                    self.handle_cancel()
                elif "SetModel" in cmd:
                    self.handle_set_model(cmd["SetModel"].get("provider", ""), cmd["SetModel"]["model_id"])
                elif "Bash" in cmd:
                    output = tool_bash(cmd["Bash"]["command"])
                    self.emit_text_message(f"```\n{output}\n```")
                elif "GetState" in cmd:
                    self.emit({"CommandResponse": {
                        "id": "getstate",
                        "command": "GetState",
                        "success": True,
                        "data": {"messages": len(self.messages), "model": self.model},
                        "error": None,
                    }})
                else:
                    log.warning("Unknown command: %s", cmd)


# ── Built-in tool implementations ────────────────────────────

def tool_read_file(path):
    """Read a file and return its contents."""
    with open(path) as f:
        return f.read()


def tool_write_file(path, content):
    """Write content to a file."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return f"Written {len(content)} bytes to {path}"


def tool_bash(command):
    """Execute a shell command, return stdout+stderr."""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += result.stderr
    if result.returncode != 0:
        output += f"\n[exit code: {result.returncode}]"
    return output or "(no output)"


def tool_grep(pattern, path=".", include=None):
    """Search for a pattern in files using rg or grep."""
    # Try ripgrep first, fall back to grep
    try:
        cmd = ["rg", "--no-heading", "-n", pattern]
        if include:
            cmd.extend(["-g", include])
        cmd.append(path)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode <= 1:
            return result.stdout or "(no matches)"
    except FileNotFoundError:
        pass

    # Fallback to grep
    cmd = ["grep", "-rn", pattern]
    if include:
        cmd.extend(["--include", include])
    cmd.append(path)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout or "(no matches)"
