from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db() -> Iterable[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                keywords TEXT NOT NULL,
                exclude_keywords TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                source_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                author TEXT NOT NULL,
                published_at TEXT NOT NULL,
                likes INTEGER NOT NULL,
                shares INTEGER NOT NULL,
                comments_count INTEGER NOT NULL,
                url TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(topic_id) REFERENCES topics(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                published_at TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(post_id) REFERENCES source_posts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                bucket TEXT NOT NULL,
                posts INTEGER NOT NULL,
                likes INTEGER NOT NULL,
                shares INTEGER NOT NULL,
                comments INTEGER NOT NULL,
                negative_posts INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                level TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def json_load(value: str) -> Any:
    return json.loads(value)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def list_topics() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM topics ORDER BY id DESC").fetchall()
    return [row_to_topic(row) for row in rows]


def row_to_topic(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "keywords": json_load(row["keywords"]),
        "exclude_keywords": json_load(row["exclude_keywords"]),
        "enabled": bool(row["enabled"]),
        "created_at": from_iso(row["created_at"]),
    }


def create_topic(name: str, keywords: list[str], exclude_keywords: list[str], enabled: bool) -> dict[str, Any]:
    created_at = now_iso()
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO topics (name, keywords, exclude_keywords, enabled, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, json_dump(keywords), json_dump(exclude_keywords), int(enabled), created_at),
        )
        topic_id = cur.lastrowid
    return get_topic(topic_id)


def get_topic(topic_id: int) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
    return row_to_topic(row) if row else None


def update_topic(topic_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
    current = get_topic(topic_id)
    if not current:
        return None
    payload = {
        "name": fields.get("name", current["name"]),
        "keywords": fields.get("keywords", current["keywords"]),
        "exclude_keywords": fields.get("exclude_keywords", current["exclude_keywords"]),
        "enabled": fields.get("enabled", current["enabled"]),
    }
    with db() as conn:
        conn.execute(
            """
            UPDATE topics
            SET name = ?, keywords = ?, exclude_keywords = ?, enabled = ?
            WHERE id = ?
            """,
            (
                payload["name"],
                json_dump(payload["keywords"]),
                json_dump(payload["exclude_keywords"]),
                int(payload["enabled"]),
                topic_id,
            ),
        )
    return get_topic(topic_id)


def insert_post(payload: dict[str, Any]) -> int | None:
    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM source_posts WHERE source_id = ?",
            (payload["source_id"],),
        ).fetchone()
        if existing:
            return None
        cur = conn.execute(
            """
            INSERT INTO source_posts
            (topic_id, platform, source_id, title, summary, author, published_at, likes, shares, comments_count, url, sentiment, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["topic_id"],
                payload["platform"],
                payload["source_id"],
                payload["title"],
                payload["summary"],
                payload["author"],
                payload["published_at"],
                payload["likes"],
                payload["shares"],
                payload["comments_count"],
                payload["url"],
                payload["sentiment"],
                payload["created_at"],
            ),
        )
        return cur.lastrowid


def insert_comment(post_id: int, content: str, published_at: str, sentiment: str) -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO comments (post_id, content, published_at, sentiment, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (post_id, content, published_at, sentiment, now_iso()),
        )


def add_snapshot(topic_id: int, platform: str, bucket: str, posts: int, likes: int, shares: int, comments: int, negative_posts: int) -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO metric_snapshots
            (topic_id, platform, bucket, posts, likes, shares, comments, negative_posts, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (topic_id, platform, bucket, posts, likes, shares, comments, negative_posts, now_iso()),
        )


def create_alert(topic_id: int, alert_type: str, level: str, reason: str, status: str = "open") -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO alerts (topic_id, alert_type, level, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (topic_id, alert_type, level, reason, status, now_iso()),
        )


def fetch_posts(topic_id: int | None = None, platform: str | None = None, sentiment: str | None = None, sort: str = "latest", limit: int = 100) -> list[dict[str, Any]]:
    query = "SELECT * FROM source_posts WHERE 1=1"
    params: list[Any] = []
    if topic_id:
        query += " AND topic_id = ?"
        params.append(topic_id)
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    if sentiment:
        query += " AND sentiment = ?"
        params.append(sentiment)
    if sort == "popular":
        query += " ORDER BY likes DESC, shares DESC, comments_count DESC"
    else:
        query += " ORDER BY published_at DESC, id DESC"
    query += " LIMIT ?"
    params.append(limit)
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [row_to_post(row) for row in rows]


def row_to_post(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "topic_id": row["topic_id"],
        "platform": row["platform"],
        "source_id": row["source_id"],
        "title": row["title"],
        "summary": row["summary"],
        "author": row["author"],
        "published_at": from_iso(row["published_at"]),
        "likes": row["likes"],
        "shares": row["shares"],
        "comments_count": row["comments_count"],
        "url": row["url"],
        "sentiment": row["sentiment"],
        "created_at": from_iso(row["created_at"]),
    }


def fetch_comments(topic_id: int | None = None, limit: int = 300) -> list[dict[str, Any]]:
    query = """
        SELECT c.* FROM comments c
        JOIN source_posts p ON c.post_id = p.id
        WHERE 1=1
    """
    params: list[Any] = []
    if topic_id:
        query += " AND p.topic_id = ?"
        params.append(topic_id)
    query += " ORDER BY c.published_at DESC, c.id DESC LIMIT ?"
    params.append(limit)
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": row["id"],
            "post_id": row["post_id"],
            "content": row["content"],
            "published_at": from_iso(row["published_at"]),
            "sentiment": row["sentiment"],
            "created_at": from_iso(row["created_at"]),
        }
        for row in rows
    ]


def fetch_alerts(topic_id: int | None = None, status: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM alerts WHERE 1=1"
    params: list[Any] = []
    if topic_id:
        query += " AND topic_id = ?"
        params.append(topic_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC, id DESC"
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": row["id"],
            "topic_id": row["topic_id"],
            "alert_type": row["alert_type"],
            "level": row["level"],
            "reason": row["reason"],
            "status": row["status"],
            "created_at": from_iso(row["created_at"]),
        }
        for row in rows
    ]


def fetch_snapshots(topic_id: int, bucket_from: str | None = None, bucket_to: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM metric_snapshots WHERE topic_id = ?"
    params: list[Any] = [topic_id]
    if bucket_from:
        query += " AND bucket >= ?"
        params.append(bucket_from)
    if bucket_to:
        query += " AND bucket <= ?"
        params.append(bucket_to)
    query += " ORDER BY bucket ASC, platform ASC"
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def seed_if_empty() -> None:
    with db() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM topics").fetchone()["n"]
    if count:
        return
    topic = create_topic(
        "城市治理与民生服务",
        ["城市治理", "民生服务", "营商环境", "政务服务"],
        ["广告", "招聘"],
        True,
    )
    from .services.collectors import collect_for_topic
    collect_for_topic(topic["id"], source="seed")
