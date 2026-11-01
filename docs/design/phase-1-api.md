# Phase 1 — API Design: Auth, Articles, Upload

Design spec for the first backend milestone. It defines **what** to build: endpoints, data, rules, errors. **How** you implement it (functions, helpers, file layout inside each module) is your call; it gets reviewed after.

---

## 1. Scope

| In scope | Out of scope (later phases) |
|---|---|
| Register, login (JWT access token), current user | Refresh tokens, roles, password reset (Phase 1B) |
| Articles: create, read, list, update, delete | Teams / team visibility |
| Article lifecycle: draft → published → retired | Approval workflow (Phase 7) |
| Article versions (history of every content change) | Diff between versions |
| Upload PDF / DOCX / MD / TXT → draft article | LLM-structured articles, background queue (Phase 2) |
| Migrations (Alembic), tests for every endpoint | Rate limiting, file virus scanning (Phase 9) |

---

## 2. Libraries

| Purpose | Package |
|---|---|
| ORM (async) | `sqlalchemy[asyncio]` |
| Postgres async driver | `asyncpg` |
| Migrations | `alembic` |
| Settings from `.env` | `pydantic-settings` |
| JWT | `pyjwt` |
| Password hashing | `pwdlib[argon2]` |
| PDF text | `pypdf` |
| DOCX text | `python-docx` |
| Tests (dev dependency: `uv add --dev`) | `pytest`, `pytest-asyncio` (or `anyio`) |

---

## 3. Project structure (layers)

```
src/knowledge_center/
├── main.py            # creates the app, includes routers
├── config.py          # Settings (pydantic-settings), read from .env
├── db.py              # async engine, session factory, get_session dependency
├── security.py        # hash/verify password, create/decode JWT
├── deps.py            # shared dependencies: get_current_user
├── models/            # SQLAlchemy tables: user.py, article.py, document.py
├── schemas/           # Pydantic request/response models: user.py, article.py, document.py
├── services/          # business logic: article_service.py, document_service.py, auth_service.py
└── routers/           # HTTP layer only: auth.py, articles.py, documents.py
```

**Rule for each layer**

| Layer | Does | Does NOT |
|---|---|---|
| `routers/` | parse the request, call a service, return a response, map errors to status codes | contain business rules or raw queries |
| `services/` | business rules (lifecycle, permissions, versioning), DB queries | know about HTTP (no `HTTPException`, no `Request`) |
| `schemas/` | define API input/output shapes and validation | touch the database |
| `models/` | define tables | contain business logic |

**Why:** services stay reusable. The agent (Phase 6) and MCP server (Phase 8) will call the *same* services without going through HTTP.

Services raise your own exceptions (e.g. `ArticleNotFound`, `InvalidTransition`); routers or a global exception handler turn them into 404 / 409.

---

## 4. Data model

All ids are **UUID**. All timestamps are **timezone-aware UTC** (`timestamptz`).

### `users`
| Column | Type | Rules |
|---|---|---|
| id | uuid | PK |
| email | text | unique, stored lowercase |
| password_hash | text | never returned by the API |
| full_name | text | nullable |
| is_active | bool | default true |
| created_at | timestamptz | default now |

### `articles`
| Column | Type | Rules |
|---|---|---|
| id | uuid | PK |
| title | text | 1–200 chars |
| body | text | markdown, required |
| status | enum `draft \| published \| retired` | default `draft` |
| visibility | enum `private \| public` | default `private` |
| owner_id | uuid | FK → users.id |
| current_version | int | starts at 1 |
| content_hash | text | sha256 of `title + "\n" + body` |
| source | enum `manual \| upload` | (`servicenow` added in Phase 12) |
| published_at | timestamptz | nullable, set on publish |
| created_at, updated_at | timestamptz | |

Indexes: `owner_id`, `(status, visibility)`.

### `article_versions`
| Column | Type | Rules |
|---|---|---|
| id | uuid | PK |
| article_id | uuid | FK → articles.id, cascade delete |
| version | int | unique together with `article_id` |
| title, body | text | snapshot of that version |
| content_hash | text | |
| created_by | uuid | FK → users.id |
| created_at | timestamptz | |

### `documents`
| Column | Type | Rules |
|---|---|---|
| id | uuid | PK |
| filename | text | original name, for display only |
| storage_path | text | where the file is saved on disk |
| mime_type | text | |
| size_bytes | int | |
| uploaded_by | uuid | FK → users.id |
| article_id | uuid | FK → articles.id, nullable |
| created_at | timestamptz | |

---

## 5. Business rules

### 5.1 Article lifecycle (state machine)

```
            publish              retire
  draft  ───────────►  published ─────────►  retired
    ▲                                          │
    └──────────────────  restore  ─────────────┘
```

| Action | Allowed from | Result |
|---|---|---|
| publish | `draft` | `published`, sets `published_at` |
| retire | `published` | `retired` |
| restore | `retired` | `draft` |
| edit title/body/visibility | `draft`, `published` | stays in same status |
| edit | `retired` | **409** — restore first |
| delete | `draft` only | hard delete (article + versions) |
| delete | `published`, `retired` | **409** — retire instead (keeps history) |

Any other transition → **409 Conflict** with a message naming the current status.

### 5.2 Versioning
- Create → version 1 written to `article_versions`.
- Update where title or body changed → compute new `content_hash`. If the hash **equals** the current one, it's a no-op: no new version. Otherwise increment `current_version` and insert a new `article_versions` row.
- Visibility-only change → no new version.
- **The article update and the version insert happen in one transaction.** Both succeed or neither does.

### 5.3 Permissions
| Who | Can see | Can modify (edit, transitions, delete) |
|---|---|---|
| Owner | all their own articles, any status | yes |
| Any other logged-in user | only `published` + `public` | no |

- Article exists but the user can't see it → **404**, not 403. A 403 would reveal that the article exists.
- Article visible but the user isn't the owner, and tries to modify → **403**.
- All `/articles` and `/documents` endpoints require login.

---

## 6. Endpoints

Errors use FastAPI's default shape: `{"detail": "message"}`. Validation errors are FastAPI's automatic **422**.

### Health
| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/health` | no | 200 `{"status": "ok"}` |

### Auth
| Method | Path | Request | Success | Errors |
|---|---|---|---|---|
| POST | `/auth/register` | JSON `{email, password, full_name?}` | **201** `UserOut` | 409 email taken; 422 invalid email or password < 8 chars |
| POST | `/auth/login` | **form data** `username` (= email), `password` | **200** `{access_token, token_type: "bearer"}` | 401 wrong email or password (same message for both) |
| GET | `/auth/me` | Bearer token | **200** `UserOut` | 401 missing/invalid/expired token |

- Login uses form data (`OAuth2PasswordRequestForm`) so the **Authorize** button in `/docs` works.
- JWT: HS256, expires in 30 minutes, `sub` = user id. Secret comes from `.env`.
- `UserOut` = `{id, email, full_name, created_at}`. Never include `password_hash`.

### Articles
| Method | Path | Request | Success | Errors |
|---|---|---|---|---|
| POST | `/articles` | `{title, body, visibility?}` | **201** `ArticleOut` (status `draft`, version 1) | 422 |
| GET | `/articles` | query: `status`, `visibility`, `q`, `mine`, `limit` (default 20, max 100), `offset` | **200** `{items: ArticleSummary[], total, limit, offset}` | 422 |
| GET | `/articles/{id}` | — | **200** `ArticleOut` | 404 |
| PATCH | `/articles/{id}` | any of `{title, body, visibility}` | **200** `ArticleOut` | 403, 404, 409 retired |
| DELETE | `/articles/{id}` | — | **204** | 403, 404, 409 not draft |
| POST | `/articles/{id}/publish` | — | **200** `ArticleOut` | 403, 404, 409 |
| POST | `/articles/{id}/retire` | — | **200** `ArticleOut` | 403, 404, 409 |
| POST | `/articles/{id}/restore` | — | **200** `ArticleOut` | 403, 404, 409 |
| GET | `/articles/{id}/versions` | — | **200** `VersionSummary[]` (newest first) | 404 |
| GET | `/articles/{id}/versions/{version}` | — | **200** `VersionOut` | 404 |

- `GET /articles` applies the permission rule from 5.3: own articles + others' published-public. `mine=true` returns only your own.
- `q` = case-insensitive search in title and body (`ILIKE` for now).
- `ArticleSummary` = everything except `body` (lists stay small). `ArticleOut` includes `body`.

### Documents (upload)
| Method | Path | Request | Success | Errors |
|---|---|---|---|---|
| POST | `/documents` | multipart `file` | **201** `{document: DocumentOut, article: ArticleOut}` | 413 file > 10 MB; 415 unsupported type; 422 no text extracted |
| GET | `/documents` | — | **200** `DocumentOut[]` (your uploads) | |
| GET | `/documents/{id}` | — | **200** `DocumentOut` | 404 |

**Upload flow**
1. Validate extension **and** content type: `.pdf`, `.docx`, `.md`, `.txt`. Reject anything else (415).
2. Enforce the 10 MB limit (413).
3. Save to `storage/uploads/<uuid><ext>`. Never use the user's filename as the path (path traversal). Add `storage/` to `.gitignore`.
4. Extract text (pypdf / python-docx / read as UTF-8).
5. Empty text (e.g. a scanned PDF) → 422 with a clear message.
6. Create a **draft** article: title = first markdown heading if present, else filename without extension; `source = upload`; version 1.
7. Create the `documents` row linked to the article.

PDF parsing is CPU work: run extraction with `asyncio.to_thread(...)` so it doesn't block the event loop.

---

## 7. Configuration (`.env`)

| Variable | Example |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_center` |
| `JWT_SECRET` | long random string (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) |
| `JWT_EXPIRE_MINUTES` | `30` |
| `UPLOAD_DIR` | `storage/uploads` |
| `MAX_UPLOAD_MB` | `10` |

Commit a `.env.example` with placeholder values. Never commit `.env`.

---

## 8. Build order

Commit after each milestone works.

| # | Milestone | Done when |
|---|---|---|
| 1 | Postgres + pgvector in `compose.yaml` | `SELECT '[1,2,3]'::vector;` works |
| 2 | `config.py` + `.env` + `.env.example` | app reads `DATABASE_URL` from `.env` |
| 3 | `db.py` + Alembic setup | `alembic upgrade head` runs against Docker Postgres |
| 4 | Users table + register / login / me | full flow works from `/docs` with the Authorize button |
| 5 | Articles table + versions + CRUD | create, list, get, patch (new version), delete draft |
| 6 | Lifecycle transitions | every row of table 5.1 behaves as specified |
| 7 | Upload | PDF, DOCX and MD each become a draft article |
| 8 | Tests | every endpoint: happy path + each listed error |

---

## 9. Acceptance tests (minimum)

- Register → login → `/auth/me` returns the same user.
- Register the same email twice → 409. Login with a wrong password → 401.
- Request without a token → 401.
- User B cannot see User A's private article (404) and cannot edit A's public published article (403).
- Edit body → `current_version` becomes 2, two rows in versions. Same body again → still version 2.
- Publish a draft → 200; publish again → 409. Retire → restore → back to draft.
- Delete a published article → 409.
- Upload a PDF → a draft article exists with the extracted text and `source = upload`.
- Upload a `.exe` → 415.

---

## 10. What the review will check

- Layers respected: no SQL in routers, no `HTTPException` in services.
- No blocking calls inside `async def`: password hashing and PDF parsing go through `asyncio.to_thread`.
- Transactions: article update + version insert are atomic.
- No N+1 queries in list endpoints.
- `password_hash` and secrets never leak into responses or logs.
- Type hints everywhere; Pydantic schemas separate from SQLAlchemy models.
- Clear names, small functions, no copy-pasted logic (e.g. one `get_article_for_user` helper reused by every endpoint).
- Tests cover the error cases, not only happy paths.

---

## 11. Interview angles from this phase

- Why 404 instead of 403 for articles you can't see?
- Why UUIDs instead of auto-increment ids in a public API?
- Why argon2/bcrypt, and why the same error for "wrong email" and "wrong password"?
- Why a service layer separate from routes?
- How do you keep the article and its version history consistent? (transactions)
- What's `content_hash` for? (no-op edits now; detecting stale RAG chunks in Phase 4)
- Why can't users delete a published article?
