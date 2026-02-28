"""RAG service — retrieval-augmented generation for Mars mission agents.

Provides knowledge retrieval (static Mars domain) and mission memory
(dynamic agent experience) to enrich agent reasoning prompts.
"""

import asyncio
import logging
import time
from pathlib import Path

from mistralai import Mistral

from .config import settings
from .db import _create_connection

logger = logging.getLogger(__name__)

# Module-level cached Mistral client
_mistral_client: Mistral | None = None

# Counter for memory pruning trigger
_memory_store_count: int = 0


def _get_mistral_client() -> Mistral:
    """Initialize and cache a Mistral client instance."""
    global _mistral_client
    if _mistral_client is None:
        if not settings.mistral_api_key:
            raise RuntimeError("MISTRAL_API_KEY not set — cannot use RAG embeddings")
        _mistral_client = Mistral(api_key=settings.mistral_api_key)
    return _mistral_client


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts via Mistral's embedding API.

    Returns list of 1024-dim float vectors.
    """
    if not texts:
        return []
    client = _get_mistral_client()
    response = client.embeddings.create(model="mistral-embed", inputs=texts)
    return [item.embedding for item in response.data]


async def _safe_rag_call(coro, default):
    """Wrap a RAG coroutine with timeout and error handling.

    Returns `default` on timeout or any exception.
    """
    try:
        return await asyncio.wait_for(coro, timeout=settings.rag_timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning("RAG call timed out after %.1fs", settings.rag_timeout_seconds)
        return default
    except Exception:
        logger.warning("RAG call failed", exc_info=True)
        return default


def _build_situation_summary(agent_id: str) -> str:
    """Build a natural language summary of an agent's current situation for embedding."""
    from .world import WORLD

    agent = WORLD["agents"].get(agent_id)
    if not agent:
        return f"Agent {agent_id} — no state available"

    x, y = agent["position"]
    battery = agent["battery"]
    memory = agent.get("memory", [])
    last_action = memory[-1] if memory else "none"
    agent_type = agent.get("type", "rover")

    parts = [
        f"{agent_type} at position ({x}, {y})",
        f"battery {battery:.0%}",
    ]

    # Current task context
    tasks = agent.get("tasks", [])
    if tasks:
        parts.append(f"task: {tasks[0]}")

    # Ground status
    ground_readings = agent.get("ground_readings", {})
    current_reading = ground_readings.get(f"{x},{y}")
    if current_reading is not None:
        parts.append(f"ground concentration {current_reading:.3f}")

    parts.append(f"last action: {last_action}")

    return ", ".join(parts)


# ── Knowledge Table (Static Mars Knowledge) ──


def init_knowledge_table():
    """Create the knowledge_chunk SurrealDB table and indexes."""
    db = _create_connection()
    try:
        db.query("DEFINE TABLE knowledge_chunk SCHEMAFULL;")
        db.query("DEFINE FIELD source ON knowledge_chunk TYPE string;")
        db.query("DEFINE FIELD section ON knowledge_chunk TYPE string;")
        db.query("DEFINE FIELD content ON knowledge_chunk TYPE string;")
        db.query("DEFINE FIELD embedding ON knowledge_chunk TYPE array<float>;")
        db.query("DEFINE FIELD category ON knowledge_chunk TYPE string;")
        db.query("DEFINE FIELD created_at ON knowledge_chunk TYPE datetime DEFAULT time::now();")
        db.query(
            "DEFINE INDEX idx_chunk_embedding ON knowledge_chunk "
            "FIELDS embedding HNSW DIMENSION 1024 DIST COSINE;"
        )
        db.query("DEFINE INDEX idx_chunk_category ON knowledge_chunk FIELDS category;")
        logger.info("Knowledge chunk table initialized")
    finally:
        db.close()


def _chunk_knowledge_document(doc_path: str) -> list[dict]:
    """Read and chunk the Mars knowledge document by section headers."""
    path = Path(doc_path)
    if not path.exists():
        logger.warning("Knowledge document not found: %s", doc_path)
        return []

    text = path.read_text()
    sections = []
    current_section = None
    current_lines = []

    category_map = {
        "terrain": "terrain",
        "geology": "geology",
        "vein": "veins",
        "concentration": "concentration",
        "battery": "battery",
        "fuel": "battery",
        "exploration": "exploration",
        "storm": "storms",
        "hazard": "storms",
        "procedure": "procedures",
        "workflow": "procedures",
        "coordination": "procedures",
    }

    for line in text.split("\n"):
        if line.startswith("## "):
            if current_section and current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    category = "terrain"  # default
                    section_lower = current_section.lower()
                    for key, cat in category_map.items():
                        if key in section_lower:
                            category = cat
                            break
                    sections.append(
                        {
                            "source": "mars_knowledge",
                            "section": current_section,
                            "content": content,
                            "category": category,
                        }
                    )
            current_section = line[3:].strip()
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)

    # Last section
    if current_section and current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            category = "terrain"
            section_lower = current_section.lower()
            for key, cat in category_map.items():
                if key in section_lower:
                    category = cat
                    break
            sections.append(
                {
                    "source": "mars_knowledge",
                    "section": current_section,
                    "content": content,
                    "category": category,
                }
            )

    return sections


def load_knowledge_chunks():
    """Embed and store knowledge chunks in SurrealDB. Idempotent."""
    db = _create_connection()
    try:
        result = db.query("SELECT count() FROM knowledge_chunk GROUP ALL;")
        existing = 0
        if result and isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "count" in r:
                    existing = r["count"]
                    break
                if isinstance(r, list):
                    for item in r:
                        if isinstance(item, dict) and "count" in item:
                            existing = item["count"]
                            break

        if existing > 0:
            logger.info("Knowledge chunks already loaded (%d), skipping", existing)
            return

        doc_path = str(Path(__file__).parent.parent / "data" / "mars_knowledge.md")
        chunks = _chunk_knowledge_document(doc_path)
        if not chunks:
            logger.warning("No knowledge chunks to load")
            return

        # Batch embed all chunk texts
        texts = [c["content"] for c in chunks]
        embeddings = _embed_texts(texts)

        for chunk, embedding in zip(chunks, embeddings):
            db.query(
                "CREATE knowledge_chunk SET "
                "source = $source, section = $section, content = $content, "
                "embedding = $embedding, category = $category;",
                {
                    "source": chunk["source"],
                    "section": chunk["section"],
                    "content": chunk["content"],
                    "embedding": embedding,
                    "category": chunk["category"],
                },
            )

        logger.info("Loaded %d knowledge chunks into SurrealDB", len(chunks))
    finally:
        db.close()


def retrieve_knowledge(agent_id: str) -> list[dict]:
    """Retrieve relevant knowledge chunks for an agent's current situation."""
    summary = _build_situation_summary(agent_id)
    if not summary:
        return []

    embeddings = _embed_texts([summary])
    if not embeddings:
        return []

    query_vector = embeddings[0]
    top_k = settings.rag_knowledge_top_k

    db = _create_connection()
    try:
        results = db.query(
            "SELECT content, source, section, vector::distance::knn() AS distance "
            "FROM knowledge_chunk "
            f"WHERE embedding <|{top_k},100|> $query_vector "
            "ORDER BY distance;",
            {"query_vector": query_vector},
        )

        chunks = []
        if results and isinstance(results, list):
            items = results[0] if results and isinstance(results[0], list) else results
            for item in items:
                if isinstance(item, dict) and "content" in item:
                    chunks.append(
                        {
                            "content": item["content"],
                            "source": item.get("source", ""),
                            "section": item.get("section", ""),
                            "distance": item.get("distance", 0),
                        }
                    )
        return chunks[:top_k]
    finally:
        db.close()


# ── Mission Memory Table (Dynamic Agent Experience) ──


def init_memory_table():
    """Create the mission_memory SurrealDB table and indexes."""
    db = _create_connection()
    try:
        db.query("DEFINE TABLE mission_memory SCHEMAFULL;")
        db.query("DEFINE FIELD agent_id ON mission_memory TYPE string;")
        db.query("DEFINE FIELD content ON mission_memory TYPE string;")
        db.query("DEFINE FIELD embedding ON mission_memory TYPE array<float>;")
        db.query("DEFINE FIELD tick ON mission_memory TYPE int;")
        db.query("DEFINE FIELD position ON mission_memory TYPE array<int>;")
        db.query("DEFINE FIELD action_name ON mission_memory TYPE string;")
        db.query("DEFINE FIELD success ON mission_memory TYPE bool;")
        db.query("DEFINE FIELD category ON mission_memory TYPE string;")
        db.query("DEFINE FIELD created_at ON mission_memory TYPE datetime DEFAULT time::now();")
        db.query(
            "DEFINE INDEX idx_memory_embedding ON mission_memory "
            "FIELDS embedding HNSW DIMENSION 1024 DIST COSINE;"
        )
        db.query("DEFINE INDEX idx_memory_agent ON mission_memory FIELDS agent_id;")
        db.query("DEFINE INDEX idx_memory_category ON mission_memory FIELDS category;")
        db.query("DEFINE INDEX idx_memory_tick ON mission_memory FIELDS tick;")
        logger.info("Mission memory table initialized")
    finally:
        db.close()


def _categorize_action(action_name: str, success: bool) -> str:
    """Map action name to memory category."""
    if not success:
        return "failure"
    mapping = {
        "move": "exploration",
        "analyze": "discovery",
        "analyze_ground": "discovery",
        "check": "discovery",
        "dig": "extraction",
        "pickup": "extraction",
        "scan": "scan",
        "charge": "charging",
        "deploy_solar_panel": "charging",
        "use_solar_battery": "charging",
    }
    return mapping.get(action_name, "exploration")


async def store_memory(agent_id: str, content: str, action_name: str, success: bool) -> None:
    """Embed and store a mission memory entry in SurrealDB."""
    global _memory_store_count
    from .world import WORLD

    agent = WORLD["agents"].get(agent_id)
    if not agent:
        return

    tick = WORLD.get("tick", 0)
    position = list(agent["position"])
    category = _categorize_action(action_name, success)

    try:
        embeddings = await asyncio.to_thread(_embed_texts, [content])
        if not embeddings:
            return

        embedding = embeddings[0]

        def _store():
            db = _create_connection()
            try:
                db.query(
                    "CREATE mission_memory SET "
                    "agent_id = $agent_id, content = $content, "
                    "embedding = $embedding, tick = $tick, "
                    "position = $position, action_name = $action_name, "
                    "success = $success, category = $category;",
                    {
                        "agent_id": agent_id,
                        "content": content,
                        "embedding": embedding,
                        "tick": tick,
                        "position": position,
                        "action_name": action_name,
                        "success": success,
                        "category": category,
                    },
                )
            finally:
                db.close()

        await asyncio.to_thread(_store)
        _memory_store_count += 1

        # Trigger pruning every 50 stores
        if _memory_store_count % 50 == 0:
            await asyncio.to_thread(prune_memories)

    except Exception:
        logger.warning("Failed to store memory for %s", agent_id, exc_info=True)


def retrieve_memories(agent_id: str, cross_agent: bool = False) -> list[dict]:
    """Retrieve relevant mission memories for an agent's current situation."""
    summary = _build_situation_summary(agent_id)
    if not summary:
        return []

    embeddings = _embed_texts([summary])
    if not embeddings:
        return []

    query_vector = embeddings[0]
    top_k = settings.rag_memory_top_k

    db = _create_connection()
    try:
        if cross_agent:
            results = db.query(
                "SELECT content, agent_id, tick, vector::distance::knn() AS distance "
                "FROM mission_memory "
                f"WHERE embedding <|{top_k},100|> $query_vector "
                "ORDER BY distance;",
                {"query_vector": query_vector},
            )
        else:
            results = db.query(
                "SELECT content, agent_id, tick, vector::distance::knn() AS distance "
                "FROM mission_memory "
                f"WHERE agent_id = $agent_id AND embedding <|{top_k},100|> $query_vector "
                "ORDER BY distance;",
                {"query_vector": query_vector, "agent_id": agent_id},
            )

        memories = []
        if results and isinstance(results, list):
            items = results[0] if results and isinstance(results[0], list) else results
            for item in items:
                if isinstance(item, dict) and "content" in item:
                    memories.append(
                        {
                            "content": item["content"],
                            "agent_id": item.get("agent_id", ""),
                            "tick": item.get("tick", 0),
                            "distance": item.get("distance", 0),
                        }
                    )
        return memories[:top_k]
    finally:
        db.close()


def prune_memories(max_entries: int = 500) -> int:
    """Delete oldest mission memories if count exceeds max_entries."""
    db = _create_connection()
    try:
        result = db.query("SELECT count() FROM mission_memory GROUP ALL;")
        total = 0
        if result and isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "count" in r:
                    total = r["count"]
                    break
                if isinstance(r, list):
                    for item in r:
                        if isinstance(item, dict) and "count" in item:
                            total = item["count"]
                            break

        if total <= max_entries:
            return 0

        excess = total - max_entries
        # Two-step delete: find oldest IDs, then delete them
        old_ids_result = db.query(
            "SELECT id, created_at FROM mission_memory ORDER BY created_at ASC LIMIT $excess;",
            {"excess": excess},
        )
        ids_to_delete = []
        if old_ids_result and isinstance(old_ids_result, list):
            items = (
                old_ids_result[0]
                if old_ids_result and isinstance(old_ids_result[0], list)
                else old_ids_result
            )
            for item in items:
                if isinstance(item, dict) and "id" in item:
                    ids_to_delete.append(item["id"])

        for record_id in ids_to_delete:
            db.query("DELETE $id;", {"id": record_id})

        deleted = len(ids_to_delete)
        logger.info("Pruned %d old mission memories (total was %d)", deleted, total)
        return deleted
    finally:
        db.close()


# ── Context Assembly ──


async def retrieve_context(agent_id: str) -> dict:
    """Retrieve relevant knowledge + memory for an agent's current situation.

    Returns dict with knowledge_chunks, memory_entries, query_text.
    Stores result in WORLD["agents"][agent_id]["rag_context"].
    """
    from .world import WORLD

    empty = {"knowledge_chunks": [], "memory_entries": [], "query_text": ""}

    if not settings.rag_enabled:
        WORLD["agents"][agent_id]["rag_context"] = empty
        return empty

    start = time.monotonic()
    summary = _build_situation_summary(agent_id)

    # Retrieve knowledge chunks
    knowledge = await _safe_rag_call(asyncio.to_thread(retrieve_knowledge, agent_id), [])

    # Retrieve mission memories (cross-agent by default)
    memories = await _safe_rag_call(asyncio.to_thread(retrieve_memories, agent_id, True), [])

    elapsed_ms = (time.monotonic() - start) * 1000
    logger.info(
        "RAG retrieval for %s: %.0fms (knowledge=%d, memories=%d)",
        agent_id,
        elapsed_ms,
        len(knowledge or []),
        len(memories or []),
    )

    context = {
        "knowledge_chunks": knowledge or [],
        "memory_entries": memories or [],
        "query_text": summary,
    }

    WORLD["agents"][agent_id]["rag_context"] = context
    return context


def format_rag_context(rag_context: dict) -> str:
    """Format retrieved RAG context as prompt text for injection into _build_context()."""
    if not rag_context:
        return ""

    parts = []
    total_chars = 0
    max_chars = settings.rag_max_context_tokens * 4  # rough chars-to-tokens

    # Knowledge chunks
    knowledge = rag_context.get("knowledge_chunks", [])
    if knowledge:
        parts.append("\n== Mars Knowledge ==")
        for chunk in knowledge:
            line = f"- {chunk['content']}"
            if total_chars + len(line) > max_chars:
                break
            parts.append(line)
            total_chars += len(line)

    # Memory entries
    memories = rag_context.get("memory_entries", [])
    if memories:
        parts.append("\n== Relevant Past Experience ==")
        for mem in memories:
            agent = mem.get("agent_id", "unknown")
            tick = mem.get("tick", "?")
            line = f"- [{agent}, tick {tick}] {mem['content']}"
            if total_chars + len(line) > max_chars:
                break
            parts.append(line)
            total_chars += len(line)

    return "\n".join(parts) if parts else ""


# ── Initialization ──


async def init_rag():
    """Initialize the RAG system: create tables and load knowledge chunks."""
    if not settings.rag_enabled:
        logger.info("RAG is disabled, skipping initialization")
        return

    try:
        logger.info("Initializing RAG system...")
        await asyncio.to_thread(init_knowledge_table)
        await asyncio.to_thread(init_memory_table)
        await asyncio.to_thread(load_knowledge_chunks)
        logger.info("RAG system initialized successfully")
    except Exception:
        logger.warning(
            "RAG initialization failed — agents will operate without RAG",
            exc_info=True,
        )
