"""Test setup: a separate database, emptied before every test."""

import os

import psycopg
import pytest

ADMIN_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
TEST_DB = "knowledge_center_test"

# Must happen before the app is imported: settings are read at import time,
# and environment variables take priority over the .env file.
os.environ["DATABASE_URL"] = f"postgresql://postgres:postgres@localhost:5432/{TEST_DB}"
os.environ["UPLOAD_DIR"] = "storage/test-uploads"

from fastapi.testclient import TestClient  # noqa: E402

from knowledge_center.db import pool  # noqa: E402
from knowledge_center.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # CREATE DATABASE can't run inside a transaction, hence autocommit.
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        exists = admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,)).fetchone()
        if not exists:
            admin.execute(f"CREATE DATABASE {TEST_DB}")

    with TestClient(app) as test_client:  # runs the app's startup: opens pool, creates tables
        yield test_client


@pytest.fixture(autouse=True)
def empty_tables(client):
    with pool.connection() as conn:
        conn.execute("TRUNCATE users, articles, article_versions, documents RESTART IDENTITY CASCADE")


def sign_up(client: TestClient, email: str) -> dict[str, str]:
    """Register and log in a user. Returns the Authorization header."""
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": email.split("@")[0]},
    )
    response = client.post("/api/auth/login", data={"username": email, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def alice(client) -> dict[str, str]:
    return sign_up(client, "alice@example.com")


@pytest.fixture
def bob(client) -> dict[str, str]:
    return sign_up(client, "bob@example.com")
