# Knowledge Center

An AI-powered knowledge base built with **FastAPI**: write and version knowledge articles, upload documents that become articles, and ask questions answered from the knowledge base with citations. It grows into an agent, a knowledge graph, and an MCP server, with RAG built by hand and no frameworks.

> **Status:** early development. Features below are the target; the [progress tracker](PROJECT_PLAN.md#9-progress-tracker) shows what's done.

## Features

- **Knowledge articles** with a lifecycle (`draft → published → retired`), versioning, ownership and visibility
- **Document upload** (PDF, DOCX, Markdown) converted into draft articles
- **RAG Q&A**: grounded answers with citations, streaming responses
- **Advanced retrieval**: hybrid search (vector + keyword with Reciprocal Rank Fusion), reranking, permission-aware retrieval, correct handling of updated and retired articles
- **Evaluation**: golden dataset, retrieval and answer-quality metrics, tracing and cost per query
- **Knowledge graph** linking articles, services and incident types for related-article and impact queries
- **AI agent** with hand-written tool calling and human approval for write actions
- **MCP server** so tools like Claude and Cursor can query the knowledge base
- **ServiceNow integration**: incremental sync of `kb_knowledge` articles
- **Deployment** on AWS

## Tech stack

| Area | Tools |
|---|---|
| Language & tooling | Python 3.12, uv, ruff, pyright, pytest |
| API | FastAPI, Pydantic v2 |
| Database | PostgreSQL + pgvector, SQLAlchemy 2.0 (async), Alembic |
| AI | Claude API, embedding models (chosen by evaluation), hand-built RAG and agent loop |
| Observability | OpenTelemetry / Langfuse |
| Deployment | Docker, AWS |

## Getting started

**Prerequisites:** [uv](https://docs.astral.sh/uv/) installed. uv installs the correct Python version automatically.

```bash
git clone <repo-url>
cd knowledge_center
uv sync          # creates .venv and installs dependencies
```

Run commands inside the project environment with `uv run`. There's no need to activate `.venv`. Commands for running the API, database and tests will be added here as each part is built.

## Project structure

```
knowledge_center/
├── src/knowledge_center/   # application code
├── PROJECT_PLAN.md         # roadmap, phases, design decisions
├── NOTES.md                # problems hit, root causes and fixes (added in Phase 0)
├── pyproject.toml          # project metadata and dependencies
└── uv.lock                 # locked dependency versions
```

## Roadmap

The full plan is in [PROJECT_PLAN.md](PROJECT_PLAN.md). In short:

1. **Foundations**: articles, versions, upload, migrations, tests
2. **RAG core**: chunking, embeddings, pgvector, answers with citations
3. **Advanced RAG**: stale-index handling, hybrid search, reranking, permissions, prompt caching
4. **Evaluation & tracing**
5. **Knowledge graph**
6. **Agent**
7. **MCP server**
8. **Full auth, background queue, multi-agent pipeline, security hardening**
9. **AWS deployment**
10. **ServiceNow integration**
