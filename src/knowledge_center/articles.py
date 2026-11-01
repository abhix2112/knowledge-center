"""Knowledge articles: create, read, list, edit, lifecycle, versions.

Who can see what:
  - your own articles, in any status
  - other people's articles only when published AND public

Lifecycle:  draft --publish--> published --retire--> retired --restore--> draft
"""

import hashlib
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from psycopg import Connection
from psycopg.rows import DictRow

from knowledge_center.auth import CurrentUser
from knowledge_center.db import DbConn
from knowledge_center.schemas import (
    ArticleCreate,
    ArticleList,
    ArticleOut,
    ArticleUpdate,
    CategoryCount,
    Status,
    UserOut,
    VersionOut,
    VersionSummary,
    Visibility,
)

router = APIRouter(tags=["articles"])

# Columns for article summaries. "a" = articles, "u" = the owner (users).
SUMMARY_COLUMNS = """
    a.id,
    'KB' || lpad(a.number::text, 7, '0') AS number,
    a.title,
    left(a.body, 240) AS excerpt,
    a.category, a.tags, a.status, a.visibility, a.source,
    a.owner_id, u.full_name AS owner_name,
    a.current_version, a.published_at, a.created_at, a.updated_at
"""
FROM_ARTICLES = "FROM articles a JOIN users u ON u.id = a.owner_id"

# SQL condition: the article is visible to the user in %(user_id)s.
VISIBLE = "(a.owner_id = %(user_id)s OR (a.status = 'published' AND a.visibility = 'public'))"


def content_hash(title: str, body: str) -> str:
    return hashlib.sha256(f"{title}\n{body}".encode()).hexdigest()


# ---------- Helpers (also used by documents.py and seed.py) ----------


def insert_article(
    conn: Connection[DictRow],
    *,
    owner_id: UUID,
    title: str,
    body: str,
    category: str = "General",
    tags: list[str] | None = None,
    visibility: Visibility = "public",
    source: str = "manual",
    status: Status = "draft",
) -> UUID:
    """Create an article and its version 1. Returns the new article id."""
    digest = content_hash(title, body)
    row = conn.execute(
        """
        INSERT INTO articles (title, body, category, tags, visibility, source, status,
                              owner_id, content_hash, published_at)
        VALUES (%(title)s, %(body)s, %(category)s, %(tags)s, %(visibility)s, %(source)s,
                %(status)s, %(owner_id)s, %(hash)s,
                CASE WHEN %(status)s = 'published' THEN now() END)
        RETURNING id
        """,
        {
            "title": title,
            "body": body,
            "category": category,
            "tags": tags or [],
            "visibility": visibility,
            "source": source,
            "status": status,
            "owner_id": owner_id,
            "hash": digest,
        },
    ).fetchone()
    conn.execute(
        """
        INSERT INTO article_versions (article_id, version, title, body, content_hash, created_by)
        VALUES (%s, 1, %s, %s, %s, %s)
        """,
        (row["id"], title, body, digest, owner_id),
    )
    return row["id"]


def get_visible_article(conn: Connection[DictRow], article_id: UUID, user: UserOut) -> ArticleOut:
    """The article, if this user may see it. Otherwise 404.

    404 rather than 403, so nobody can probe which private articles exist.
    """
    row = conn.execute(
        f"SELECT {SUMMARY_COLUMNS}, a.body {FROM_ARTICLES} WHERE a.id = %(id)s AND {VISIBLE}",
        {"id": article_id, "user_id": user.id},
    ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    return ArticleOut(**row)


def get_own_article(conn: Connection[DictRow], article_id: UUID, user: UserOut) -> ArticleOut:
    """The article, if this user owns it. 404 if invisible, 403 if visible but not theirs."""
    article = get_visible_article(conn, article_id, user)
    if article.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner can change this article")
    return article


# ---------- Endpoints ----------


@router.get("/categories")
def list_categories(user: CurrentUser, conn: DbConn) -> list[CategoryCount]:
    rows = conn.execute(
        f"""
        SELECT a.category, count(*) AS count
        FROM articles a
        WHERE {VISIBLE}
        GROUP BY a.category
        ORDER BY a.category
        """,
        {"user_id": user.id},
    ).fetchall()
    return [CategoryCount(**row) for row in rows]


@router.get("/articles")
def list_articles(
    user: CurrentUser,
    conn: DbConn,
    q: str | None = Query(default=None, description="Search title, body or KB number"),
    status_filter: Status | None = Query(default=None, alias="status"),
    category: str | None = None,
    mine: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ArticleList:
    # Build the WHERE clause from the filters that were given.
    conditions = [VISIBLE]
    params: dict[str, Any] = {"user_id": user.id, "limit": limit, "offset": offset}

    if q:
        conditions.append(
            "(a.title ILIKE %(q)s OR a.body ILIKE %(q)s"
            " OR 'KB' || lpad(a.number::text, 7, '0') ILIKE %(q)s)"
        )
        params["q"] = f"%{q}%"
    if status_filter:
        conditions.append("a.status = %(status)s")
        params["status"] = status_filter
    if category:
        conditions.append("a.category = %(category)s")
        params["category"] = category
    if mine:
        conditions.append("a.owner_id = %(user_id)s")

    # count(*) OVER () adds the total number of matches to every row,
    # so we get the page and the total in one query.
    rows = conn.execute(
        f"""
        SELECT {SUMMARY_COLUMNS}, count(*) OVER () AS total
        {FROM_ARTICLES}
        WHERE {" AND ".join(conditions)}
        ORDER BY a.updated_at DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        params,
    ).fetchall()

    total = rows[0]["total"] if rows else 0
    return ArticleList(items=rows, total=total, limit=limit, offset=offset)


@router.post("/articles", status_code=status.HTTP_201_CREATED)
def create_article(data: ArticleCreate, user: CurrentUser, conn: DbConn) -> ArticleOut:
    article_id = insert_article(
        conn,
        owner_id=user.id,
        title=data.title,
        body=data.body,
        category=data.category,
        tags=data.tags,
        visibility=data.visibility,
    )
    return get_visible_article(conn, article_id, user)


@router.get("/articles/{article_id}")
def get_article(article_id: UUID, user: CurrentUser, conn: DbConn) -> ArticleOut:
    return get_visible_article(conn, article_id, user)


@router.patch("/articles/{article_id}")
def update_article(
    article_id: UUID, data: ArticleUpdate, user: CurrentUser, conn: DbConn
) -> ArticleOut:
    article = get_own_article(conn, article_id, user)
    if article.status == "retired":
        raise HTTPException(status.HTTP_409_CONFLICT, "Retired articles can't be edited. Restore it first.")

    title = data.title if data.title is not None else article.title
    body = data.body if data.body is not None else article.body
    new_hash = content_hash(title, body)
    content_changed = new_hash != content_hash(article.title, article.body)
    version = article.current_version + 1 if content_changed else article.current_version

    conn.execute(
        """
        UPDATE articles SET
            title = %(title)s,
            body = %(body)s,
            category = coalesce(%(category)s, category),
            tags = coalesce(%(tags)s, tags),
            visibility = coalesce(%(visibility)s, visibility),
            content_hash = %(hash)s,
            current_version = %(version)s,
            updated_at = now()
        WHERE id = %(id)s
        """,
        {
            "id": article_id,
            "title": title,
            "body": body,
            "category": data.category,
            "tags": data.tags,
            "visibility": data.visibility,
            "hash": new_hash,
            "version": version,
        },
    )
    if content_changed:
        conn.execute(
            """
            INSERT INTO article_versions (article_id, version, title, body, content_hash, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (article_id, version, title, body, new_hash, user.id),
        )
    return get_visible_article(conn, article_id, user)


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: UUID, user: CurrentUser, conn: DbConn) -> Response:
    article = get_own_article(conn, article_id, user)
    if article.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only drafts can be deleted. This article is {article.status}; retire it instead.",
        )
    conn.execute("DELETE FROM articles WHERE id = %s", (article_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Lifecycle ----------

Action = Literal["publish", "retire", "restore"]

# action -> (status it must be in now, status it moves to)
TRANSITIONS: dict[Action, tuple[Status, Status]] = {
    "publish": ("draft", "published"),
    "retire": ("published", "retired"),
    "restore": ("retired", "draft"),
}


@router.post("/articles/{article_id}/{action}")
def change_status(article_id: UUID, action: Action, user: CurrentUser, conn: DbConn) -> ArticleOut:
    article = get_own_article(conn, article_id, user)
    required, new_status = TRANSITIONS[action]
    if article.status != required:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Can't {action} an article that is {article.status}. It must be {required}.",
        )
    conn.execute(
        """
        UPDATE articles SET
            status = %(status)s,
            published_at = CASE WHEN %(status)s = 'published' THEN now() ELSE published_at END,
            updated_at = now()
        WHERE id = %(id)s
        """,
        {"id": article_id, "status": new_status},
    )
    return get_visible_article(conn, article_id, user)


# ---------- Versions ----------


@router.get("/articles/{article_id}/versions")
def list_versions(article_id: UUID, user: CurrentUser, conn: DbConn) -> list[VersionSummary]:
    get_visible_article(conn, article_id, user)  # 404 if the user can't see it
    rows = conn.execute(
        """
        SELECT v.version, v.title, u.full_name AS created_by_name, v.created_at
        FROM article_versions v JOIN users u ON u.id = v.created_by
        WHERE v.article_id = %s
        ORDER BY v.version DESC
        """,
        (article_id,),
    ).fetchall()
    return [VersionSummary(**row) for row in rows]


@router.get("/articles/{article_id}/versions/{version}")
def get_version(article_id: UUID, version: int, user: CurrentUser, conn: DbConn) -> VersionOut:
    get_visible_article(conn, article_id, user)
    row = conn.execute(
        """
        SELECT v.version, v.title, v.body, u.full_name AS created_by_name, v.created_at
        FROM article_versions v JOIN users u ON u.id = v.created_by
        WHERE v.article_id = %s AND v.version = %s
        """,
        (article_id, version),
    ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found")
    return VersionOut(**row)
