"""Comprehensive tests for the RAG service module (app/rag.py).

Covers knowledge generation, chunking, embedding, situation summaries,
context formatting, action categorization, safe call wrapper, and
SurrealDB table/memory operations.
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.config import settings
from app.rag import (
    _build_situation_summary,
    _categorize_action,
    _chunk_knowledge_document,
    _embed_texts,
    _safe_rag_call,
    format_rag_context,
    init_knowledge_table,
    init_memory_table,
    prune_memories,
)
from app.world import WORLD

from conftest import CaseWithDB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_embedding(dim=1024):
    """Create a mock embedding response matching Mistral's API shape."""
    mock_data = MagicMock()
    mock_data.embedding = [0.1] * dim
    mock_response = MagicMock()
    mock_response.data = [mock_data]
    return mock_response


def _mock_client(dim=1024):
    """Build a mock Mistral client whose embeddings.create returns vectors."""
    client = MagicMock()
    client.embeddings.create.return_value = _mock_embedding(dim)
    return client


SAMPLE_MARKDOWN = """\
# Mars Knowledge

## Terrain Info
Rocky surface with craters.
Temperature varies widely.

## Geology Details
Basalt veins found in lava tubes.
High mineral concentration near craters.

## Storm Hazards
Dust storms reduce visibility.
Stay close to station.
"""


# ---------------------------------------------------------------------------
# 1. TestKnowledgeGeneration
# ---------------------------------------------------------------------------


class TestKnowledgeGeneration(unittest.TestCase):
    """Tests for generate_knowledge() from rag_setup."""

    def test_generate_knowledge_creates_file(self):
        """generate_knowledge() writes mars_knowledge.md into server/data/."""
        from app.rag_setup import generate_knowledge, KNOWLEDGE_PATH

        generate_knowledge()
        self.assertTrue(KNOWLEDGE_PATH.exists(), "mars_knowledge.md was not created")

    def test_generate_knowledge_has_all_sections(self):
        """The generated document contains all 8 expected ## sections."""
        from app.rag_setup import generate_knowledge, KNOWLEDGE_PATH

        generate_knowledge()
        text = KNOWLEDGE_PATH.read_text()

        expected_sections = [
            "Terrain",
            "Geology",
            "Vein",
            "Concentration",
            "Battery",
            "Exploration",
            "Storm",
            "Procedures",
        ]
        for section in expected_sections:
            # Each section starts with "## ... <keyword> ..."
            self.assertIn(
                section,
                text,
                f"Section keyword '{section}' missing from knowledge document",
            )

    def test_generate_knowledge_contains_constants(self):
        """World model constants appear in the generated knowledge document."""
        from app.rag_setup import generate_knowledge, KNOWLEDGE_PATH
        from app.world import FUEL_CAPACITY_ROVER, MEMORY_MAX, VEIN_GRADES

        generate_knowledge()
        text = KNOWLEDGE_PATH.read_text()

        self.assertIn(
            str(FUEL_CAPACITY_ROVER),
            text,
            "FUEL_CAPACITY_ROVER value missing",
        )
        self.assertIn(
            str(MEMORY_MAX),
            text,
            "MEMORY_MAX value missing",
        )
        for grade in VEIN_GRADES:
            self.assertIn(
                grade.capitalize(),
                text,
                f"Vein grade '{grade}' missing from knowledge document",
            )


# ---------------------------------------------------------------------------
# 2. TestKnowledgeSchema
# ---------------------------------------------------------------------------


class TestKnowledgeSchema(CaseWithDB):
    """Tests for the knowledge_chunk SurrealDB table."""

    async def test_init_knowledge_table(self):
        """init_knowledge_table() creates the knowledge_chunk table."""
        init_knowledge_table()
        result = self.db.query("INFO FOR TABLE knowledge_chunk;")
        # SurrealDB returns table info — presence without error is sufficient
        self.assertIsNotNone(result)

    async def test_knowledge_table_accepts_records(self):
        """A record with all required fields can be stored and retrieved."""
        init_knowledge_table()
        self.db.query(
            "CREATE knowledge_chunk SET "
            "source = $source, section = $section, content = $content, "
            "embedding = $embedding, category = $category;",
            {
                "source": "test",
                "section": "Terrain",
                "content": "Rocky surface data",
                "embedding": [0.1] * 1024,
                "category": "terrain",
            },
        )

        rows = self.db.query("SELECT * FROM knowledge_chunk;")
        # Flatten if nested list
        items = rows[0] if rows and isinstance(rows[0], list) else rows
        self.assertTrue(len(items) >= 1, "Record was not stored")
        record = items[0]
        self.assertEqual(record["source"], "test")
        self.assertEqual(record["section"], "Terrain")
        self.assertEqual(record["content"], "Rocky surface data")
        self.assertEqual(record["category"], "terrain")


# ---------------------------------------------------------------------------
# 3. TestChunkDocument
# ---------------------------------------------------------------------------


class TestChunkDocument(unittest.TestCase):
    """Tests for _chunk_knowledge_document()."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._doc_path = os.path.join(self._tmpdir, "test_knowledge.md")
        with open(self._doc_path, "w") as f:
            f.write(SAMPLE_MARKDOWN)

    def tearDown(self):
        if os.path.exists(self._doc_path):
            os.remove(self._doc_path)
        os.rmdir(self._tmpdir)

    def test_chunk_knowledge_document(self):
        """Chunks have correct source, section, content, and category fields."""
        chunks = _chunk_knowledge_document(self._doc_path)

        self.assertEqual(len(chunks), 3)

        # First chunk — terrain
        self.assertEqual(chunks[0]["source"], "mars_knowledge")
        self.assertEqual(chunks[0]["section"], "Terrain Info")
        self.assertIn("Rocky surface", chunks[0]["content"])
        self.assertEqual(chunks[0]["category"], "terrain")

        # Second chunk — geology
        self.assertEqual(chunks[1]["section"], "Geology Details")
        self.assertEqual(chunks[1]["category"], "geology")

        # Third chunk — storm
        self.assertEqual(chunks[2]["section"], "Storm Hazards")
        self.assertEqual(chunks[2]["category"], "storms")

    def test_chunk_empty_doc(self):
        """An empty or missing document returns an empty list."""
        # Missing file
        self.assertEqual(_chunk_knowledge_document("/nonexistent/file.md"), [])

        # Empty file
        empty_path = os.path.join(self._tmpdir, "empty.md")
        with open(empty_path, "w") as f:
            f.write("")
        self.assertEqual(_chunk_knowledge_document(empty_path), [])
        os.remove(empty_path)

    def test_chunk_no_header_doc(self):
        """A document with no ## headers returns an empty list."""
        no_header_path = os.path.join(self._tmpdir, "no_header.md")
        with open(no_header_path, "w") as f:
            f.write("Just some plain text without any section headers.\n")
        self.assertEqual(_chunk_knowledge_document(no_header_path), [])
        os.remove(no_header_path)


# ---------------------------------------------------------------------------
# 4. TestEmbedding
# ---------------------------------------------------------------------------


class TestEmbedding(unittest.TestCase):
    """Tests for _embed_texts()."""

    @patch("app.rag._get_mistral_client")
    def test_embed_texts_returns_vectors(self, mock_get_client):
        """Mocked Mistral embedding returns 1024-dim vectors."""
        mock_get_client.return_value = _mock_client(1024)

        result = _embed_texts(["test sentence"])

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 1024)
        self.assertTrue(all(v == 0.1 for v in result[0]))

    def test_embed_empty_returns_empty(self):
        """An empty input list returns [] without calling Mistral."""
        result = _embed_texts([])
        self.assertEqual(result, [])

    @patch("app.rag._get_mistral_client")
    def test_embed_multiple_texts(self, mock_get_client):
        """Multiple inputs produce one vector each."""
        mock_data_1 = MagicMock()
        mock_data_1.embedding = [0.2] * 1024
        mock_data_2 = MagicMock()
        mock_data_2.embedding = [0.3] * 1024
        mock_response = MagicMock()
        mock_response.data = [mock_data_1, mock_data_2]

        client = MagicMock()
        client.embeddings.create.return_value = mock_response
        mock_get_client.return_value = client

        result = _embed_texts(["text one", "text two"])

        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0][0], 0.2)
        self.assertAlmostEqual(result[1][0], 0.3)


# ---------------------------------------------------------------------------
# 5. TestSituationSummary
# ---------------------------------------------------------------------------


class TestSituationSummary(unittest.TestCase):
    """Tests for _build_situation_summary()."""

    def setUp(self):
        # Inject a test agent into the global WORLD
        WORLD["agents"]["test-agent"] = {
            "position": [5, 5],
            "battery": 0.8,
            "type": "rover",
            "memory": ["Moved north to (5,5)"],
            "tasks": ["Explore area"],
            "visited": [],
            "rag_context": {},
        }
        WORLD["tick"] = 10

    def tearDown(self):
        WORLD["agents"].pop("test-agent", None)

    def test_build_situation_summary(self):
        """Summary includes position, battery, type, task, and last action."""
        summary = _build_situation_summary("test-agent")

        self.assertIn("(5, 5)", summary)
        self.assertIn("80%", summary)
        self.assertIn("rover", summary)
        self.assertIn("Explore area", summary)
        self.assertIn("Moved north to (5,5)", summary)

    def test_build_situation_summary_no_memory(self):
        """Agent with no memory shows 'none' for last action."""
        WORLD["agents"]["test-agent"]["memory"] = []
        summary = _build_situation_summary("test-agent")

        self.assertIn("none", summary)

    def test_build_situation_summary_unknown_agent(self):
        """Non-existent agent returns a fallback string."""
        summary = _build_situation_summary("nonexistent-agent")

        self.assertIn("nonexistent-agent", summary)
        self.assertIn("no state", summary)

    def test_build_situation_summary_with_ground_reading(self):
        """Summary includes ground concentration when available."""
        WORLD["agents"]["test-agent"]["ground_readings"] = {"5,5": 0.753}
        summary = _build_situation_summary("test-agent")

        self.assertIn("0.753", summary)


# ---------------------------------------------------------------------------
# 6. TestFormatRagContext
# ---------------------------------------------------------------------------


class TestFormatRagContext(unittest.TestCase):
    """Tests for format_rag_context()."""

    def test_format_knowledge_chunks(self):
        """Output contains the Mars Knowledge header and chunk content."""
        ctx = {
            "knowledge_chunks": [
                {"content": "Rocky terrain data", "source": "test", "section": "Terrain"},
            ],
            "memory_entries": [],
        }
        result = format_rag_context(ctx)

        self.assertIn("== Mars Knowledge ==", result)
        self.assertIn("Rocky terrain data", result)

    def test_format_memory_entries(self):
        """Output contains Relevant Past Experience header with [agent, tick N] format."""
        ctx = {
            "knowledge_chunks": [],
            "memory_entries": [
                {
                    "content": "Discovered basalt vein",
                    "agent_id": "rover-1",
                    "tick": 42,
                },
            ],
        }
        result = format_rag_context(ctx)

        self.assertIn("== Relevant Past Experience ==", result)
        self.assertIn("[rover-1, tick 42]", result)
        self.assertIn("Discovered basalt vein", result)

    def test_format_empty_returns_empty(self):
        """An empty dict (or None-ish) returns an empty string."""
        self.assertEqual(format_rag_context({}), "")
        self.assertEqual(format_rag_context(None), "")

    def test_format_respects_token_limit(self):
        """Very large chunks are truncated by rag_max_context_tokens."""
        original_limit = settings.rag_max_context_tokens
        try:
            # Set a very small token limit so the output gets truncated
            settings.rag_max_context_tokens = 10  # 10 tokens ~ 40 chars max

            big_content = "A" * 5000
            ctx = {
                "knowledge_chunks": [
                    {"content": big_content, "source": "test", "section": "Big"},
                    {"content": "Should not appear", "source": "test", "section": "Two"},
                ],
                "memory_entries": [],
            }
            result = format_rag_context(ctx)

            # The full 5000-char content should NOT fit within 40-char budget
            self.assertNotIn("Should not appear", result)
        finally:
            settings.rag_max_context_tokens = original_limit

    def test_format_both_knowledge_and_memory(self):
        """Both sections appear when both have entries."""
        ctx = {
            "knowledge_chunks": [
                {"content": "terrain info", "source": "kb", "section": "Terrain"},
            ],
            "memory_entries": [
                {"content": "memory entry", "agent_id": "r1", "tick": 5},
            ],
        }
        result = format_rag_context(ctx)

        self.assertIn("== Mars Knowledge ==", result)
        self.assertIn("== Relevant Past Experience ==", result)


# ---------------------------------------------------------------------------
# 7. TestCategorizeAction
# ---------------------------------------------------------------------------


class TestCategorizeAction(unittest.TestCase):
    """Tests for _categorize_action()."""

    def test_move_categorized_as_exploration(self):
        self.assertEqual(_categorize_action("move", True), "exploration")

    def test_analyze_categorized_as_discovery(self):
        self.assertEqual(_categorize_action("analyze", True), "discovery")

    def test_analyze_ground_categorized_as_discovery(self):
        self.assertEqual(_categorize_action("analyze_ground", True), "discovery")

    def test_failed_action_categorized_as_failure(self):
        """Any action with success=False returns 'failure'."""
        self.assertEqual(_categorize_action("move", False), "failure")
        self.assertEqual(_categorize_action("analyze", False), "failure")
        self.assertEqual(_categorize_action("dig", False), "failure")
        self.assertEqual(_categorize_action("scan", False), "failure")
        self.assertEqual(_categorize_action("charge", False), "failure")

    def test_scan_categorized_as_scan(self):
        self.assertEqual(_categorize_action("scan", True), "scan")

    def test_dig_categorized_as_extraction(self):
        self.assertEqual(_categorize_action("dig", True), "extraction")

    def test_pickup_categorized_as_extraction(self):
        self.assertEqual(_categorize_action("pickup", True), "extraction")

    def test_charge_categorized_as_charging(self):
        self.assertEqual(_categorize_action("charge", True), "charging")

    def test_deploy_solar_panel_categorized_as_charging(self):
        self.assertEqual(_categorize_action("deploy_solar_panel", True), "charging")

    def test_unknown_action_defaults_to_exploration(self):
        """An unrecognized action name defaults to 'exploration'."""
        self.assertEqual(_categorize_action("unknown_action", True), "exploration")


# ---------------------------------------------------------------------------
# 8. TestSafeRagCall
# ---------------------------------------------------------------------------


class TestSafeRagCall(unittest.IsolatedAsyncioTestCase):
    """Tests for _safe_rag_call() timeout and error handling."""

    async def test_timeout_returns_default(self):
        """A coroutine that exceeds the timeout returns the default value."""
        original = settings.rag_timeout_seconds
        try:
            settings.rag_timeout_seconds = 0.1  # very short timeout

            async def slow():
                await asyncio.sleep(10)
                return "should not get here"

            result = await _safe_rag_call(slow(), default="fallback")
            self.assertEqual(result, "fallback")
        finally:
            settings.rag_timeout_seconds = original

    async def test_exception_returns_default(self):
        """A coroutine that raises returns the default value."""

        async def failing():
            raise ValueError("boom")

        result = await _safe_rag_call(failing(), default=[])
        self.assertEqual(result, [])

    async def test_success_returns_result(self):
        """A coroutine that completes normally passes its value through."""

        async def ok():
            return {"data": 42}

        result = await _safe_rag_call(ok(), default=None)
        self.assertEqual(result, {"data": 42})

    async def test_success_with_none_default(self):
        """Successful result is returned even when default is also provided."""

        async def ok():
            return "value"

        result = await _safe_rag_call(ok(), default="default")
        self.assertEqual(result, "value")


# ---------------------------------------------------------------------------
# 9. TestMemorySchema
# ---------------------------------------------------------------------------


class TestMemorySchema(CaseWithDB):
    """Tests for the mission_memory SurrealDB table."""

    async def test_init_memory_table(self):
        """init_memory_table() creates the mission_memory table."""
        init_memory_table()
        result = self.db.query("INFO FOR TABLE mission_memory;")
        self.assertIsNotNone(result)

    async def test_memory_table_accepts_records(self):
        """A record with all required fields can be stored and retrieved."""
        init_memory_table()
        self.db.query(
            "CREATE mission_memory SET "
            "agent_id = $agent_id, content = $content, "
            "embedding = $embedding, tick = $tick, "
            "position = $position, action_name = $action_name, "
            "success = $success, category = $category;",
            {
                "agent_id": "rover-test",
                "content": "Moved north successfully",
                "embedding": [0.5] * 1024,
                "tick": 7,
                "position": [3, 4],
                "action_name": "move",
                "success": True,
                "category": "exploration",
            },
        )

        rows = self.db.query("SELECT * FROM mission_memory;")
        items = rows[0] if rows and isinstance(rows[0], list) else rows
        self.assertTrue(len(items) >= 1, "Memory record was not stored")
        record = items[0]
        self.assertEqual(record["agent_id"], "rover-test")
        self.assertEqual(record["tick"], 7)
        self.assertEqual(record["success"], True)
        self.assertEqual(record["category"], "exploration")

    async def test_memory_table_multiple_records(self):
        """Multiple records can be inserted and counted."""
        init_memory_table()
        for i in range(5):
            self.db.query(
                "CREATE mission_memory SET "
                "agent_id = $agent_id, content = $content, "
                "embedding = $embedding, tick = $tick, "
                "position = $position, action_name = $action_name, "
                "success = $success, category = $category;",
                {
                    "agent_id": "rover-test",
                    "content": f"Action {i}",
                    "embedding": [0.1 * i] * 1024,
                    "tick": i,
                    "position": [i, i],
                    "action_name": "move",
                    "success": True,
                    "category": "exploration",
                },
            )

        result = self.db.query("SELECT count() FROM mission_memory GROUP ALL;")
        count = 0
        if result and isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "count" in r:
                    count = r["count"]
                    break
                if isinstance(r, list):
                    for item in r:
                        if isinstance(item, dict) and "count" in item:
                            count = item["count"]
                            break
        self.assertEqual(count, 5)


# ---------------------------------------------------------------------------
# 10. TestPruneMemories
# ---------------------------------------------------------------------------


class TestPruneMemories(CaseWithDB):
    """Tests for prune_memories()."""

    def _insert_memories(self, n: int):
        """Insert n memory records into the test DB."""
        for i in range(n):
            self.db.query(
                "CREATE mission_memory SET "
                "agent_id = $agent_id, content = $content, "
                "embedding = $embedding, tick = $tick, "
                "position = $position, action_name = $action_name, "
                "success = $success, category = $category;",
                {
                    "agent_id": "rover-test",
                    "content": f"Memory entry {i}",
                    "embedding": [0.01 * i] * 1024,
                    "tick": i,
                    "position": [i, 0],
                    "action_name": "move",
                    "success": True,
                    "category": "exploration",
                },
            )

    async def test_prune_under_limit(self):
        """When record count is under the limit, prune deletes nothing."""
        init_memory_table()
        self._insert_memories(10)

        deleted = prune_memories(max_entries=500)
        self.assertEqual(deleted, 0)

        # Verify all 10 still exist
        result = self.db.query("SELECT count() FROM mission_memory GROUP ALL;")
        count = 0
        if result and isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "count" in r:
                    count = r["count"]
                    break
                if isinstance(r, list):
                    for item in r:
                        if isinstance(item, dict) and "count" in item:
                            count = item["count"]
                            break
        self.assertEqual(count, 10)

    async def test_prune_over_limit(self):
        """When record count exceeds the limit, oldest entries are removed."""
        init_memory_table()
        self._insert_memories(20)

        deleted = prune_memories(max_entries=15)
        self.assertEqual(deleted, 5)

        # Verify exactly 15 remain
        result = self.db.query("SELECT count() FROM mission_memory GROUP ALL;")
        count = 0
        if result and isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "count" in r:
                    count = r["count"]
                    break
                if isinstance(r, list):
                    for item in r:
                        if isinstance(item, dict) and "count" in item:
                            count = item["count"]
                            break
        self.assertEqual(count, 15)

    async def test_prune_exact_limit(self):
        """When count equals max_entries, nothing is pruned."""
        init_memory_table()
        self._insert_memories(10)

        deleted = prune_memories(max_entries=10)
        self.assertEqual(deleted, 0)


if __name__ == "__main__":
    unittest.main()
