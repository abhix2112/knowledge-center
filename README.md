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

**Prerequisites:** [uv](https://docs.astral.sh/uv/) and Docker. uv installs the correct Python version automatically.

```bash
git clone <repo-url>
cd knowledge_center
uv sync                                    # create .venv and install dependencies
cp .env.example .env                       # then set JWT_SECRET to a long random string
docker compose up -d                       # start Postgres with pgvector
uv run python -m knowledge_center.seed     # load 25 demo articles and 3 demo users
uv run fastapi dev src/knowledge_center/main.py
```

Open http://127.0.0.1:8000 for the app, and http://127.0.0.1:8000/docs for the API.

Demo users (password `password123`): `alice@halden.example`, `bob@halden.example`, `priya@halden.example`.

Other commands:

```bash
uv run pytest                                      # API tests (use a separate test database)
uv run python -m knowledge_center.seed --reset     # delete everything and reload the demo data
```

Run every command from the project folder. There's no need to activate `.venv`; `uv run` uses it.

## Project structure

```
knowledge_center/
├── src/knowledge_center/
│   ├── main.py          # creates the app, mounts the API and the frontend
│   ├── config.py        # settings from .env
│   ├── db.py            # Postgres connection pool
│   ├── schema.sql       # tables (applied on startup)
│   ├── schemas.py       # request/response models (Pydantic)
│   ├── security.py      # password hashing, JWT
│   ├── auth.py          # /api/auth: register, login, me
│   ├── articles.py      # /api/articles: CRUD, lifecycle, versions
│   ├── documents.py     # /api/documents: upload → draft article
│   ├── extract.py       # text from PDF, DOCX, Markdown
│   └── seed.py          # demo data loader
├── frontend/            # plain HTML/CSS/JS, served by FastAPI at /
├── seed/articles/       # demo articles as Markdown files
├── tests/               # pytest API tests
├── compose.yaml         # Postgres + pgvector
└── PROJECT_PLAN.md      # roadmap, phases, design decisions
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
