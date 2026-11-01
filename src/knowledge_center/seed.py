"""Load demo users and articles from seed/articles/*.md.

Run from the project root:
    uv run python -m knowledge_center.seed           # add what's missing
    uv run python -m knowledge_center.seed --reset   # delete everything first
"""

import argparse
from pathlib import Path

from knowledge_center.articles import insert_article
from knowledge_center.db import create_tables, pool
from knowledge_center.security import hash_password

SEED_DIR = Path(__file__).resolve().parents[2] / "seed" / "articles"
DEMO_PASSWORD = "password123"

DEMO_USERS = {
    "alice": ("alice@halden.example", "Alice Moreno"),  # IT Service Desk
    "bob": ("bob@halden.example", "Bob Okafor"),  # Security team
    "priya": ("priya@halden.example", "Priya Nair"),  # People team (HR)
}


def parse_article_file(path: Path) -> tuple[dict[str, str], str]:
    """Split a file into its front matter (the key: value lines between ---) and body."""
    text = path.read_text()
    _, header, body = text.split("---\n", 2)
    fields = {}
    for line in header.strip().splitlines():
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, body.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load demo users and articles")
    parser.add_argument("--reset", action="store_true", help="delete all data first")
    args = parser.parse_args()

    pool.open()
    create_tables()
    with pool.connection() as conn:
        if args.reset:
            conn.execute("TRUNCATE users, articles, article_versions, documents RESTART IDENTITY CASCADE")
            print("Deleted all data.")

        user_ids = {}
        for key, (email, full_name) in DEMO_USERS.items():
            row = conn.execute(
                """
                INSERT INTO users (email, password_hash, full_name) VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name
                RETURNING id
                """,
                (email, hash_password(DEMO_PASSWORD), full_name),
            ).fetchone()
            user_ids[key] = row["id"]

        added = 0
        for path in sorted(SEED_DIR.glob("*.md")):
            fields, body = parse_article_file(path)
            exists = conn.execute("SELECT 1 FROM articles WHERE title = %s", (fields["title"],)).fetchone()
            if exists:
                continue
            insert_article(
                conn,
                owner_id=user_ids[fields["owner"]],
                title=fields["title"],
                body=body,
                category=fields["category"],
                tags=[tag.strip() for tag in fields["tags"].split(",")],
                visibility=fields["visibility"],
                status=fields["status"],
                source="seed",
            )
            added += 1
    pool.close()

    print(f"Added {added} articles. Demo users (password: {DEMO_PASSWORD}):")
    for email, full_name in DEMO_USERS.values():
        print(f"  {email:<24} {full_name}")


if __name__ == "__main__":
    main()
