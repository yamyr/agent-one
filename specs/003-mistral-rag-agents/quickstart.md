# Quickstart: Mistral RAG-Enhanced Agent Intelligence

**Branch**: `003-mistral-rag-agents`

## Prerequisites

1. SurrealDB running on port 4002 (`surreal start`)
2. `MISTRAL_API_KEY` set in `server/.env` (must have embeddings API access)
3. Python dependencies: `mistralai` (already installed), `surrealdb` (already installed)

## Setup Steps

### 1. Generate Mars Knowledge Document

```bash
cd server
python -m app.rag_setup generate-knowledge
# Creates: server/data/mars_knowledge.md
```

### 2. Initialize RAG Tables

```bash
cd server
python -m app.rag_setup init-db
# Creates knowledge_chunk and mission_memory tables in SurrealDB
# Embeds and stores all knowledge chunks
```

### 3. Upload to Mistral Libraries (Optional)

```bash
cd server
python -m app.rag_setup upload-library
# Uploads mars_knowledge.md to Mistral Libraries API
# Prints library ID for future reference
```

### 4. Run the Server

```bash
cd server
./run
# RAG system initializes automatically during app startup
# Agents now use RAG-enhanced reasoning
```

## Verification

### Check Knowledge Chunks in SurrealDB

```bash
surreal sql --conn ws://localhost:4002 --ns dev --db mars \
  --user root --pass root \
  -q "SELECT count() FROM knowledge_chunk GROUP ALL"
```

### Check Mission Memory Growth

```bash
surreal sql --conn ws://localhost:4002 --ns dev --db mars \
  --user root --pass root \
  -q "SELECT count() FROM mission_memory GROUP ALL"
```

### Verify Agent Reasoning Shows RAG Context

Watch the UI event log or server logs for agent thinking messages that include Mars-specific knowledge references.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `rag_enabled` | `true` | Enable/disable RAG retrieval |
| `rag_knowledge_top_k` | `3` | Number of knowledge chunks to retrieve per tick |
| `rag_memory_top_k` | `3` | Number of memory entries to retrieve per tick |
| `rag_timeout_seconds` | `2.0` | Max time for RAG retrieval before fallback |
| `rag_max_context_tokens` | `800` | Max tokens of RAG context injected into prompt |

## Architecture Overview

```
Agent Tick Loop
  │
  ├─ 1. retrieve_context(agent_id)     ← NEW: RAG retrieval
  │     ├─ Embed situation summary (Mistral embeddings API)
  │     ├─ Query knowledge_chunk table (SurrealDB vector search)
  │     └─ Query mission_memory table (SurrealDB vector search)
  │
  ├─ 2. _build_context()               ← MODIFIED: inject RAG sections
  │     ├─ ... existing sections ...
  │     ├─ == Mars Knowledge ==         ← NEW section
  │     └─ == Relevant Past Experience == ← NEW section
  │
  ├─ 3. chat.complete()                ← UNCHANGED
  │
  ├─ 4. execute_action()               ← UNCHANGED
  │
  └─ 5. store_memory(agent_id, ...)    ← NEW: embed + store in SurrealDB
```
