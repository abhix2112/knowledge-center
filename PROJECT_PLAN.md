# AI Knowledge Center — Project Plan

> A learning project built for **senior AI engineer interview prep**.
> The goal is not just a working app: I should be able to explain *every* design decision, trade-off, and failure mode in an interview, because I built and broke it myself.

---

## 1. Context

**Who I am**
- Background: JavaScript/Node.js and Rust. Comfortable with backend concepts (REST, JSON, auth, databases).
- New to Python. Learning Python **through this project**, not through tutorials or toy apps.
- Preparing for a job change to a **Senior AI Engineer** role.

**How this project is run**
- **I write all backend code myself.** The AI assistant teaches, explains, gives tasks, and reviews my code — it does not write the backend for me.
- Learning style: build real features → write code → make mistakes → fix them. No long video courses.
- **Interview priority drives the order.** The AI phases (RAG, advanced RAG, evals, knowledge graph, agent, MCP) are what interviews test first, so they come first on top of a *lite* foundation. Full auth, queues, multi-agent, hardening, Docker and AWS come after.
- **Target: RAG, advanced RAG, evals, agent and MCP all working by Day 20.** Track 2 (foundations, hardening, AWS, ServiceNow) runs roughly Days 21–35. Depth over speed.
- **`NOTES.md` is a first-class artifact** (Section 11): one entry per problem — what broke, why, the fix, what I'd do differently. These entries *are* my interview answers.
- **Mock-interview checkpoints** after Phases 1, 3, 5, 6 and 8, using the Section 8 question bank against my own code and `NOTES.md`.
- Frontend is **deferred** — FastAPI's `/docs` (Swagger UI) is enough to demo. Terraform/CDK is deferred until the first AWS deploy works.
- After this project: **2–3 more real-world projects** (Section 12).

---

## 2. What we are building

An **AI-powered Knowledge Center** (similar in spirit to the ServiceNow Knowledge Base), with:

1. **Knowledge articles** — write, edit, version, publish, and retire articles.
2. **Document upload → article** — upload PDF/DOCX/Markdown; it is converted into a knowledge article (plain text extraction first, LLM-structured later).
3. **RAG Q&A** — ask questions in natural language; get answers grounded in the knowledge base, with citations.
4. **Knowledge graph** — entities and relationships between articles, services/CIs and incident types; "related articles" and impact questions; graph retrieval compared against vector retrieval.
5. **AI agent** — an assistant that uses the knowledge base through tools (search, read, draft articles), with approvals for write actions.
6. **MCP server** — expose the knowledge base so external AI tools (Claude, Cursor, etc.) can query it.
7. **Users & auth** — simple `user_id` first; full JWT, refresh tokens and roles (user / editor / admin) in Track 2.
8. **Ingestion pipeline with a real queue**, **multi-agent review pipeline**, **production hardening**.
9. **ServiceNow as an ingestion source** — incremental sync of `kb_knowledge` from a PDI; Knowledge Center MCP ↔ ServiceNow MCP.
10. **Deployed on AWS** with a public URL (one deploy; IaC afterwards).

---

## 3. Tech stack (and why)

| Area | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Industry standard for AI engineering |
| Package/env manager | **uv** | Fast, replaces pip + venv + pyenv; like npm/cargo |
| Web framework | **FastAPI** | Async, type-hint driven, auto OpenAPI docs (`/docs` doubles as the demo UI) |
| Validation | **Pydantic v2** | Request/response schemas, settings, LLM structured outputs |
| ORM + migrations | **SQLAlchemy 2.0 (async) + Alembic** | Industry standard; teaches real DB patterns |
| Database | **PostgreSQL + pgvector** | One DB for relational data *and* vectors; no extra vector DB to operate |
| Knowledge graph | Postgres tables + recursive CTEs first → **Neo4j** only if traversal gets painful | Learn what a graph DB actually buys you |
| Background jobs | FastAPI `BackgroundTasks` first → real queue (Redis + ARQ/Celery; SQS on AWS) in Track 2 | Hit the limit first, then fix it |
| File storage | Local disk first → AWS S3 | Same reason |
| LLM | Claude API (behind my own thin client abstraction) | Abstraction lets me swap providers, route models, add fallbacks |
| Embeddings | Two candidates evaluated on the golden set (e.g. an API model such as Voyage/OpenAI vs an open-source model such as bge/e5) | Pick by measured recall, latency, cost — not by default |
| Document parsing | pypdf / python-docx first → Docling or Unstructured for complex docs | Learn where simple parsing breaks (tables, scanned PDFs) |
| External source | **ServiceNow REST Table API** (PDI) | Real enterprise KB source; incremental sync |
| Testing | pytest + httpx | Unit + API tests |
| Code quality | ruff (lint/format), pyright or mypy (types) | Senior-level hygiene |
| Observability | Structured logging → OpenTelemetry / Langfuse for LLM tracing | Trace every RAG/agent step, cost, latency |
| Containers | docker compose for local Postgres from Day 1; Dockerfile for the app in Track 2 | Local parity, needed for AWS |
| Cloud | AWS — App Runner *or* ECS Fargate + RDS + S3 (one deploy) | IaC (Terraform/CDK) only after it works |
| Frontend | Deferred (React/Next.js, built by the AI assistant if ever needed) | `/docs` is the demo |

**Rule:** build RAG and the agent **by hand first** (no LangChain / LlamaIndex). Frameworks only later, as a comparison, so I can explain what they do under the hood.

---

## 4. High-level architecture

```
  Browser / curl /        ┌──────────────┐
  Swagger /docs    ─────► │   FastAPI    │ ──► PostgreSQL (+ pgvector)
  MCP clients             │   (API +     │       users, articles, versions,
  (Claude, Cursor) ─────► │   MCP server)│       chunks + embeddings,
                          └──────┬───────┘       entities + relationships (graph),
                                 │               jobs, sync_state
                    enqueue job  │
                                 ▼                 ┌──────────┐
                          ┌──────────────┐ ◄─────► │  S3 /    │
  ServiceNow PDI ───────► │   Worker     │         │  disk    │  uploaded files
  (kb_knowledge,          │ parse → chunk│         └──────────┘
   incremental sync)      │ → embed →    │ ──► LLM API / Embedding API
                          │ index → graph│
                          └──────────────┘

  Query path:  question → embed → hybrid search (vector + keyword, RRF)
               → permission filter → graph expansion (optional) → rerank
               → cache-aware prompt → LLM → answer + citations
```

### Core data model (initial sketch — will evolve)

- **users** — id, email, password_hash (Track 2), role, created_at. *In Track 1 a user is just an id passed in a header.*
- **articles** — id, title, body, status (`draft | published | retired`), visibility (`private | team | public`), owner_id, current_version, source (`manual | upload | servicenow`), external_id, timestamps
- **article_versions** — article_id, version, body, content_hash, created_by, created_at
- **documents** — id, filename, storage_path, mime_type, uploaded_by, status, linked article_id
- **chunks** — id, article_id, article_version, chunk_index, text, embedding (vector), content_hash, is_active, metadata
- **entities** — id, type (`service | ci | incident_type | product | team`), name, external_id, metadata
- **relationships** — from (article or entity), to (article or entity), type (`references | supersedes | relates_to | affects | documents`), source (`extracted | manual`), confidence
- **ingestion_jobs** — id, document_id, status, error, attempts, timestamps
- **sync_state** — source (`servicenow`), watermark (`sys_updated_on`), last_run, status
- **conversations / messages** — the agent's chat history
- **feedback** — message_id, helpful (yes/no), comment → feeds evaluation

---

## 5. Python concepts covered (learned inside the project, not separately)

- Data types: str, int, float, bool, None, list, tuple, dict, set — mutability, copying
- Type hints: `list[str]`, `dict[str, int]`, `X | None`, `Literal`, generics, `TypedDict`, `Protocol`
- Functions: `*args`, `**kwargs`, default args (and the mutable-default trap), lambdas
- Comprehensions (list/dict/set), generators, `yield`, iterators
- Classes, dataclasses vs Pydantic models, Enums, inheritance vs composition
- Decorators (how FastAPI's `@app.get` works)
- Context managers (`with`, `async with`) — DB sessions, files
- Exceptions: custom exceptions, FastAPI exception handlers
- Modules, packages, imports, `src/` layout, `__init__.py`
- **async / await**, the event loop, blocking vs non-blocking, `asyncio.gather` (parallel tool calls)
- Dependency injection with `Depends` (including `yield` dependencies)
- Pydantic: validation, serialization, `Field`, validators, settings from env vars, JSON schema generation (for tool definitions)
- Testing with pytest: fixtures, mocking, async tests
- Packaging & tooling: uv, pyproject.toml, lock files, ruff, pyright

---

## 6. Roadmap

**Phase numbers are stable IDs** (so the other chat and I can refer to "Phase 4" unambiguously). **The order below is the execution order.** Each phase lists: **build**, **learn**, and **interview questions it prepares me for**.

### Execution order

| # | Phase | Days | Deliverable |
|---|---|---|---|
| **Track 1 — AI core (by Day 20)** | | | |
| 1 | Phase 0 — Setup | 1 | Project runs, Postgres + pgvector up, health endpoint |
| 2 | Phase 1A — Foundations (lite) | 1–3 | Articles CRUD + versions, upload → draft, Alembic, tests |
| 🎤 | Mock interview 1 | — | Python / FastAPI questions |
| 3 | Phase 3 — RAG core | 4–6 | Grounded answers with citations, streaming |
| 🎤 | Mock interview 2 | — | RAG end-to-end |
| 4 | Phase 4 — Advanced RAG | 7–10 | Stale index solved, hybrid + RRF, rerank, permission-aware retrieval, prompt caching v1 |
| 5 | Phase 5 — Evals + tracing | 11–12 | Golden set, metrics in CI, tracing, embedding-model comparison |
| 🎤 | Mock interview 3 | — | Advanced RAG + evaluation |
| 6 | Phase 5.5 — Knowledge graph | 13–14 | Entities/relationships, related articles, graph vs vector comparison |
| 7 | Phase 6 — Agent | 15–18 | Hand-written tool loop, context engineering, approvals |
| 🎤 | Mock interview 4 | — | Agents, structured outputs, context engineering |
| 8 | Phase 8 — MCP server | 19–20 | KB queryable from Claude / Cursor |
| 🎤 | Mock interview 5 | — | Full run-through; MCP |
| **Track 2 — Foundations, hardening, cloud (Days 21+)** | | | |
| 9 | Phase 1B — Full auth | 21–22 | JWT, refresh tokens, roles |
| 10 | Phase 2 — Ingestion pipeline (real queue) | 23–24 | Worker, retries, idempotency, LLM-structured articles |
| 11 | Phase 7 — Multi-agent pipeline | 25–26 | Ingest → review → publish with approval |
| 12 | Phase 9 — Security & hardening | 27–29 | Prompt injection, routing/fallbacks, caching v2, rate limits, load test |
| 13 | Phase 11 — Docker + AWS (one deploy) | 30–33 | Public URL on App Runner or ECS Fargate + RDS + S3 |
| 14 | Phase 12 — ServiceNow source | 34+ (slowly) | Incremental `kb_knowledge` sync, MCP ↔ MCP |
| — | Phase 10 — Frontend | deferred | Only if ever needed |
| — | IaC (Terraform/CDK) | after first deploy | |

---

### Phase 0 — Setup (Day 1, half a day)
- **Build:** uv project (`src/` layout), ruff + pyright, Postgres + pgvector via docker compose (or a local install), `.env` config with Pydantic Settings, health-check endpoint, `NOTES.md` created.
- **Learn:** uv workflow, project layout, environment config.

### Phase 1A — Foundations, lite (Days 1–3)

> **Status (2026-11-01): done, built by Claude** so I could focus on the AI phases. It's simpler than the original spec below: psycopg 3 with plain SQL instead of SQLAlchemy, `schema.sql` applied on startup instead of Alembic, sync `def` endpoints, and full JWT login (register / login / me) instead of the `user_id` stub. Also includes a plain HTML/JS frontend, 25 demo articles (`seed/articles/`) and 17 API tests. **From Phase 3 (RAG) on, I write the code myself.** I still need to read through this code to learn the Python patterns in it.
- **Build:**
  - **Auth stub:** `get_current_user` dependency that reads a `user_id` from a header (or a fixed dev user). This is the *single seam* that full JWT replaces in Phase 1B — endpoints never change. Ownership and visibility already work off this `user_id`, so Phase 4's permission-aware retrieval is testable with multiple users.
  - Articles CRUD with lifecycle: `draft → published → retired`, ownership, visibility, **versioning** (`article_versions`, `content_hash`).
  - Pagination, filtering, search (Postgres `ILIKE` / full-text first).
  - Document upload: PDF/DOCX/MD → extract text → create a **draft** article. Synchronous (or `BackgroundTasks`) for now — the pain will justify Phase 2.
  - **Alembic migrations**, error handling, **tests for every endpoint**.
- **Learn:** most of Section 5; REST design in FastAPI; SQLAlchemy async sessions; migrations.
- **Interview:** how `Depends` works and `yield` dependencies; sync vs async endpoints; N+1 queries; migrations in production; why versioning and content hashes matter later for RAG.

> 🎤 **Mock interview 1** — Section 8 "Python / FastAPI" block. Answer from my own code. Weak answers → `NOTES.md` entries or study items.

### Phase 3 — RAG core, built by hand (Days 4–6)
- **Build:**
  - Chunking (fixed-size with overlap → heading/structure-aware).
  - Embeddings + store in pgvector; HNSW index.
  - Retrieval: top-k vector search, **only from published + permitted articles**.
  - Generation: prompt with retrieved chunks → answer **with citations** (article + section).
  - "I don't know" when retrieval confidence is low.
  - Streaming responses (Server-Sent Events).
- **Learn:** what embeddings are, cosine similarity, ANN indexes (HNSW vs IVFFlat), context window limits, prompt construction.
- **Interview:** explain RAG end to end; chunk size trade-offs; why not just put everything in the context window; RAG vs fine-tuning (first pass).

> 🎤 **Mock interview 2** — Section 8 "RAG" block (core questions).

### Phase 4 — Advanced RAG & real-world problems (Days 7–10)
- **Build & solve:**
  - **Stale index problem:** article updated/retired → old chunks must stop being returned. Content hashing + versioning + incremental re-indexing; soft-deactivate old chunks (`is_active`).
  - **Embedding model migration:** switching models means re-embedding everything — blue/green index (build new, switch, delete old).
  - **Hybrid search:** vector + keyword (BM25 / Postgres full-text), combined with **Reciprocal Rank Fusion**. Exact terms (error codes, IDs) need keyword search.
  - **Reranking** with a cross-encoder / rerank API.
  - **Query rewriting**, multi-query, HyDE; **contextual retrieval** (prepend document context to each chunk before embedding).
  - **Permission-aware retrieval:** user A must never get answers from user B's private docs. Filter *inside* the query, not after.
  - **Latency budget:** measure each step (embed query, search, rerank, LLM); then optimize — caching, streaming, smaller models for sub-steps.
  - **Prompt caching v1:** lay out the RAG prompt cache-aware — static system prompt and instructions first, retrieved chunks and the question last. **Measure tokens, latency and cost before/after** and record the numbers.
  - **Semantic cache:** reuse answers for near-identical questions (and when *not* to — permissions, freshness).
- **Interview:** "Why is RAG slow and how do you fix it?", "How do you handle document updates/deletions in RAG?", "How do you stop data leaking across users/tenants?", "Vector search misses exact matches — why and what do you do?", "How does prompt caching work and what did it save you?"

### Phase 5 — Evaluation & observability (Days 11–12)
- **Build:**
  - Golden dataset: questions + expected source articles + reference answers.
  - Retrieval metrics: recall@k, MRR, precision.
  - Generation metrics: faithfulness/groundedness, answer relevance — LLM-as-judge (and its weaknesses).
  - **Embedding model evaluation:** compare **two embedding models** on the golden set (recall@k, latency, cost, vector size/storage) **before committing to one**. Record the decision and numbers in `NOTES.md`.
  - Run evals in CI; fail on regressions.
  - Tracing for every request (Langfuse / OpenTelemetry): prompts, chunks, latency, tokens, **cost per query**.
  - User feedback (👍/👎) feeding back into the eval set.
- **Interview:** "How do you know your RAG system got better after a change?", "How did you pick your embedding model?", "How do you evaluate an LLM app?", "How do you monitor LLM quality in production?"

> 🎤 **Mock interview 3** — Section 8 "RAG" (advanced) + "Evaluation & cost" blocks. **Write design doc 1: the RAG platform** (Section 10).

### Phase 5.5 — Knowledge graph (Days 13–14)
- **Build:**
  - Extract **entities** (services / configuration items (CIs), incident types, products, teams) and **relationships** from articles with an LLM using structured outputs; store in Postgres (`entities`, `relationships`; traversal with recursive CTEs). Move to **Neo4j** only if Postgres traversal becomes painful — and write down why.
  - Relationship types: article ↔ article (`references`, `supersedes`), article ↔ service/CI (`documents`, `affects`), article ↔ incident type.
  - **"Related articles"** endpoint driven by the graph.
  - **Impact questions:** "which articles are affected if service X changes?", "what do we know about incident type Y?"
  - **Graph-augmented retrieval:** vector top-k → expand via graph neighbours → rerank. Compare **graph vs vector vs hybrid** on the golden set and **document when each wins**.
  - Keep the graph in sync with the article lifecycle (same stale problem as chunks).
- **Learn:** entity extraction quality and its failure modes, graph modelling, recursive queries, what GraphRAG actually adds.
- **Interview:** "When does a knowledge graph beat vector search?", "GraphRAG basics — what does the graph add?", "How do you keep the graph correct when articles change?", "Postgres vs a graph database — when do you switch?"

### Phase 6 — AI agent (Days 15–18)
- **Build:**
  - **Tool calling from scratch:** write the agent loop yourself (model → tool call → execute → result → model…).
  - **Function-calling internals:** tool schemas generated from Pydantic (`model_json_schema()`); **schema enforcement** on tool inputs; **retries on invalid JSON / invalid arguments** with the error fed back to the model; **parallel tool calls** (model returns several calls at once → execute concurrently with `asyncio.gather`, return results in order).
  - Tools: `search_kb`, `get_article`, `related_articles` (graph), `draft_article`, `list_recent_changes`.
  - **Context engineering:** decide and document what goes in the **system prompt** vs **retrieved context** vs **tool results**; summarise long histories; **write down what gets lost on compaction** and test it (ask about something from early in a long conversation after summarisation).
  - Conversation memory (short-term history + summarisation when long).
  - Guardrails: max steps, timeouts, tool input validation, **human approval for write actions**.
  - Stream agent steps to the client.
- **Interview:** agent vs workflow (and when *not* to use an agent); how tool calling works under the hood; what you do when the model returns invalid JSON; parallel tool calls; handling infinite loops; agent cost control; context engineering decisions.

> 🎤 **Mock interview 4** — Section 8 "Agents", "Structured outputs & function calling", "Context engineering" blocks. **Write design doc 2: the agent platform with approvals** (Section 10).

### Phase 8 — MCP server (Days 19–20)
- **Build:** expose the knowledge base as an **MCP server** (tools: `search_kb`, `get_article`, `related_articles`; resources: articles). Connect it to Claude Desktop / Claude Code / Cursor and query the KB from there.
- **Interview:** what MCP is and why it exists; tools vs resources vs prompts; auth for MCP servers; MCP vs plain REST APIs.

> 🎤 **Mock interview 5** — full run-through of Section 8 so far, end to end, as if it were the real interview.

> ✅ **Day 20 milestone:** RAG, advanced RAG, evals, knowledge graph, agent and MCP all working and explainable.

---

### Phase 1B — Full auth (Days 21–22)
- **Build:** register/login, password hashing (bcrypt/argon2), **JWT access tokens + refresh tokens**, roles (user / editor / admin), role checks on endpoints. Swap the Phase 1A header stub inside `get_current_user` — no endpoint changes.
- **Interview:** JWT vs sessions, refresh-token rotation, where tokens live, why hashing not encryption, RBAC in FastAPI.

### Phase 2 — Ingestion pipeline with a real queue (Days 23–24)
- **Build:**
  - Move upload processing to a real worker (Redis + ARQ/Celery; SQS later on AWS); job status endpoint; retries; **idempotency**.
  - LLM converts raw extracted text into a structured article (title, summary, sections, tags) using **structured outputs** (Pydantic schema) — with **schema enforcement and retries on invalid JSON**.
  - Duplicate detection: warn if an uploaded doc is near-identical to an existing article (embeddings).
- **Learn:** why long work must not run in the request; queues; idempotency; parsing failures (tables, scanned PDFs → OCR).
- **Interview:** how to process a 500-page PDF upload; what happens if the worker crashes mid-job; at-least-once vs exactly-once; structured outputs vs free-text parsing.

### Phase 7 — Multi-agent pipeline (Days 25–26)
- **Build:** document comes in → **Ingestion agent** (structure it) → **Reviewer agent** (quality, duplicates, missing info) → **Publisher** (human-in-the-loop approval).
- Compare hand-written orchestration vs a framework (e.g. LangGraph) — what the framework actually gives you.
- **Interview:** orchestrator-worker vs pipeline patterns; when multi-agent is overkill; state passing; failure handling between agents.

### Phase 9 — Security & production hardening (Days 27–29)
- **Build:**
  - **Prompt injection** defence: uploaded documents may contain "ignore previous instructions…" — treat retrieved text as data, isolate it, test with malicious docs.
  - **Model routing and fallbacks:** cheap model for classification / query rewriting / extraction, strong model for generation; provider fallback, retries, timeouts. **Measure cost per query before/after routing.**
  - **Prompt caching v2:** cache system prompt + tool definitions for the agent; measure.
  - Rate limiting per user, request size limits, file type validation.
  - PII detection/redaction on upload.
  - Prompt versioning.
  - Load test the RAG endpoint.
- **Interview:** OWASP Top 10 for LLMs; prompt injection (direct vs indirect); cost control at scale; multi-tenancy; how you decided which model handles what.

> **Write design doc 3: scaling to 1M requests/day** (Section 10) — after Phase 9, refined after Phase 11.

### Phase 11 — Docker + AWS, one deploy (Days 30–33)
Never used AWS before → learn by deploying this project. **Scope is one working deploy, not a full platform.**
- **Before anything:** IAM user with least privilege, **billing budget + alerts**.
- **Dockerize** the API and worker (Dockerfile, multi-stage build).
- **Compute:** **App Runner** (simplest) *or* **ECS Fargate** — pick one.
- **Database:** **RDS PostgreSQL** with pgvector.
- **Storage:** **S3** for uploads (pre-signed URLs).
- **Secrets:** Secrets Manager / SSM Parameter Store.
- **Logs:** CloudWatch.
- **CI/CD:** GitHub Actions → test → build → deploy.
- **Later, only after the deploy works:** Terraform or CDK; SQS for the worker queue; ALB + ACM + Route 53 for a custom domain.
- **Interview:** design and cost this system on AWS; scaling the worker; zero-downtime deploys; where secrets live.

### Phase 12 — ServiceNow as an ingestion source (Day 34+, extend slowly)
- **Build:**
  - Get a free ServiceNow **PDI** (Personal Developer Instance).
  - Pull `kb_knowledge` via the **REST Table API** (`/api/now/table/kb_knowledge`): field selection, pagination (`sysparm_limit` / `sysparm_offset`), **incremental sync on `sys_updated_on`** with a stored watermark in `sync_state`; idempotent upserts keyed on `sys_id`.
  - Map ServiceNow `workflow_state` to our lifecycle (`published` / `retired`); HTML body → text/markdown; run through the same ingestion → index → graph pipeline; handle retires/deletes so the index stays correct.
  - Connect the Knowledge Center's **MCP server to a ServiceNow MCP** so each can query the other (our agent can call ServiceNow tools; a ServiceNow-side agent can search our KB).
- **Interview:** incremental sync design (watermark vs CDC); idempotent upserts; mapping an external lifecycle onto yours; cross-system agents via MCP.

### Phase 10 — Frontend (deferred)
- FastAPI `/docs` is the demo surface. Build a UI (login, editor, upload status, streaming chat with citations) only if a specific interview needs a visual demo and time remains after AWS. Built by the AI assistant when asked.

---

## 7. Senior-level topics to master through this project

Beyond "I built a RAG app", a senior AI engineer is expected to discuss:

- **Trade-offs:** RAG vs fine-tuning vs long context; pgvector vs dedicated vector DB (Pinecone, Qdrant, Weaviate); Postgres graph vs Neo4j; build vs framework.
- **Evaluation-driven development:** no change ships without eval numbers; embedding models chosen by measurement.
- **Cost & latency engineering:** tokens per request, **prompt caching** (cache-aware prompt layout), semantic cache, **model routing**, batching embeddings — all with before/after numbers.
- **Context engineering:** what belongs in the system prompt vs retrieved vs tool results; history summarisation; what is lost on compaction.
- **Structured outputs & function calling internals:** schema enforcement, retries on invalid output, parallel tool calls.
- **Reliability:** retries, timeouts, fallbacks, idempotent jobs, graceful degradation when the LLM is down.
- **Data lifecycle:** freshness, versioning, deletions (including "right to be forgotten"), re-indexing at scale, keeping graph and index in sync.
- **Knowledge graphs / GraphRAG:** when graph retrieval beats vector retrieval, and when it doesn't.
- **Security:** prompt injection, data leakage across tenants, PII, guardrails.
- **Observability:** tracing LLM calls, debugging a bad answer back to the chunk that caused it.
- **Agents:** when to use them, when a fixed workflow is better, controlling cost and loops, approvals.
- **Fine-tuning awareness (explain-only, not built):** when fine-tuning beats RAG (consistent style/format, domain language, latency-critical narrow tasks, very large static knowledge) and when it doesn't (fast-changing facts, citations, per-user access control); LoRA/QLoRA basics; embedding fine-tuning; how you'd evaluate a fine-tune.
- **Awareness topics** (explain, maybe not build): agentic RAG, multimodal RAG (images/tables), long-context strategies.

---

## 8. Interview question bank (answer each from my own project experience and `NOTES.md`)

**Python / FastAPI** *(Mock 1)*
- async vs sync endpoints — what happens if you block the event loop?
- How does `Depends` work? How do `yield` dependencies clean up?
- Pydantic v2 validation and serialization; dataclass vs Pydantic model.
- SQLAlchemy sessions, transactions, N+1 queries, migrations.

**RAG — core** *(Mock 2)*
- Walk me through your RAG pipeline end to end.
- How did you choose chunk size and overlap? What happened when you changed it?
- Why not just put everything in the context window? RAG vs fine-tuning?
- How do you reduce hallucinations? What happens when nothing relevant is found?

**RAG — advanced** *(Mock 3)*
- A user updates or deletes an article — how does your index stay correct?
- How do you re-index when you change embedding models, without downtime?
- Why is your RAG slow? Where does the time go? What did you optimize?
- Vector search misses exact keywords — how did you fix it? What is RRF?
- How do you prevent answers from documents a user shouldn't see?
- How does prompt caching work? How did you lay out your prompt for it, and what did it save?

**Evaluation & cost** *(Mock 3)*
- How do you evaluate retrieval and generation quality? What's your golden set?
- How did you pick your embedding model? Show the numbers.
- LLM-as-judge — where does it fail?
- How do you track and reduce cost per query?

**Knowledge graph** *(Mock 4)*
- When does a knowledge graph beat vector search? When is it worse?
- GraphRAG basics — what does the graph add to RAG?
- How did you extract entities and relationships? How good was it?
- How do you keep the graph correct when articles change?

**Agents** *(Mock 4)*
- How does tool calling actually work under the hood?
- Agent vs workflow — when do you choose which?
- How do you stop an agent looping forever or burning money?
- How do you make write actions safe?
- When is multi-agent worth it?

**Structured outputs & function calling** *(Mock 4)*
- How do you enforce the output schema? What happens on invalid JSON?
- How do you handle parallel tool calls?
- Structured outputs vs parsing free text — trade-offs.

**Context engineering** *(Mock 4)*
- What belongs in the system prompt vs retrieved context vs tool results?
- How do you handle a conversation that exceeds the context window?
- What gets lost on compaction, and how did you test it?

**MCP** *(Mock 5)*
- What is MCP and why does it exist? Tools vs resources vs prompts.
- MCP vs a REST API. How do you secure an MCP server?

**Systems & production** *(Track 2)*
- How do you process large uploads reliably? Worker crashes mid-job?
- How do you handle LLM provider outages and rate limits? How did you decide which model handles what?
- How do you defend against prompt injection from uploaded documents?
- JWT vs sessions; refresh-token rotation.
- How is this deployed on AWS, and how would it scale to 10× users?

**ServiceNow integration** *(Phase 12)*
- How did you sync `kb_knowledge` incrementally? Watermark vs CDC?
- How do you handle deletes/retires from the source?
- How do two MCP servers work together?

**AI system design** *(design docs, Section 10)*
- Design a RAG platform for a company's internal knowledge.
- Design an agent platform with human approvals.
- Scale it to 1M requests/day — where does it break first?

**Fine-tuning (explain-only)**
- When would you fine-tune instead of RAG? What is LoRA? How would you evaluate it?

---

## 9. Progress tracker

**Track 1 — AI core (target: Day 20)**
- [x] Phase 0 — Setup (`NOTES.md` still to create)
- [x] Phase 1A — Foundations, lite (built by Claude, simplified; see Phase 1A status)
- [ ] 🎤 Mock interview 1
- [ ] Phase 3 — RAG core
- [ ] 🎤 Mock interview 2
- [ ] Phase 4 — Advanced RAG (incl. prompt caching v1)
- [ ] Phase 5 — Evals + tracing (incl. embedding-model comparison)
- [ ] 🎤 Mock interview 3 · 📄 Design doc 1: RAG platform
- [ ] Phase 5.5 — Knowledge graph
- [ ] Phase 6 — Agent (incl. function-calling internals, context engineering)
- [ ] 🎤 Mock interview 4 · 📄 Design doc 2: agent platform with approvals
- [ ] Phase 8 — MCP server
- [ ] 🎤 Mock interview 5
- [ ] ✅ Day 20 milestone

**Track 2 — Foundations, hardening, cloud**
- [ ] Phase 1B — Full auth (register/login/JWT already done; refresh tokens and roles remain)
- [ ] Phase 2 — Ingestion pipeline with real queue
- [ ] Phase 7 — Multi-agent pipeline
- [ ] Phase 9 — Security & hardening (incl. routing/fallbacks, caching v2)
- [ ] 📄 Design doc 3: scaling to 1M requests/day
- [ ] Phase 11 — Docker + AWS (one deploy)
- [ ] IaC (Terraform/CDK) — after first deploy
- [ ] Phase 12 — ServiceNow ingestion + MCP ↔ MCP
- [ ] Phase 10 — Frontend (deferred / optional)

---

## 10. Study topics outside coding (read/watch alongside)

- RAG fundamentals: embeddings, vector similarity, chunking, retrieval, reranking (watch a RAG deep-dive before Phase 3).
- How LLMs work at a high level: tokens, context windows, temperature, sampling, prompt caching.
- Agent design patterns (e.g. Anthropic's "Building effective agents"); context engineering.
- Knowledge graphs and GraphRAG basics (before Phase 5.5).
- MCP specification basics (before Phase 8).
- Fine-tuning / LoRA at a conceptual level (Section 7).
- AWS fundamentals for the services in Phase 11.
- ServiceNow REST Table API and `kb_knowledge` schema (before Phase 12).

**AI system design docs** — one page + one diagram each, stored in `docs/design/`, written at the end of the phase named:
1. **The RAG platform** — after Phase 5 (ingestion, indexing, retrieval, permissions, freshness, evals).
2. **The agent platform with approvals** — after Phase 6 (tool loop, memory, guardrails, approval flow, cost control).
3. **Scaling to 1M requests/day** — after Phase 9, refined after Phase 11 (queues, caching layers, DB/vector scaling, model routing, what breaks first).

Each doc is practice for the "design X" interview round: problem, constraints, architecture, trade-offs, failure modes, what I'd do with more time.

---

## 11. `NOTES.md` — the interview-answer log

A first-class artifact, kept in the repo root, updated **as problems happen**, not at the end. One entry per problem. These entries are the raw material for every "tell me about a time…" and "how did you handle…" question, and for the mock-interview checkpoints.

Entry template:

```markdown
## <short title>  — Phase X, Day N
**What broke:** what I saw (error, wrong answer, slow request, leaked data…)
**Why:** the actual root cause, not the symptom
**Fix:** what I changed, with numbers where relevant (before/after latency, recall@k, cost)
**What I'd do differently:** the design lesson; how I'd avoid or detect it next time
**Interview angle:** which Section 8 question this answers
```

Also log *decisions* the same way (embedding model choice, Postgres vs Neo4j, App Runner vs Fargate): options considered, numbers, choice, and what would change the decision.

---

## 12. Next projects (after this one)

Each adds skills this project does not fully cover:

1. **AI support-ticket resolution system** — incoming tickets are classified, routed, and auto-answered using a knowledge base (can reuse this project via MCP, and ServiceNow incidents via Phase 12). Focus: workflows vs agents, human-in-the-loop, SLAs, evaluation on realistic ticket data.
2. **Codebase Q&A / code-review agent** — index a GitHub repo, answer questions about it, review pull requests. Focus: code-aware chunking (AST), long-context strategies, GitHub integration, agent tool design.
3. **LLM gateway / platform service** — a service all AI apps call through: model routing, fallbacks, rate limiting, caching, cost tracking per team, prompt versioning, tracing. Focus: infrastructure-level senior skills; very strong interview story.
4. *(Optional)* **Document extraction pipeline** — invoices/contracts → validated structured data with confidence scores and a review queue. Focus: structured outputs, multimodal models, evaluation with exact metrics.
