"""
PostgreSQL memory backend — implements the same interface as SQLiteMemoryBackend.

Used when DATABASE_URL starts with "postgresql://" or "postgres://".
Requires psycopg2-binary (or psycopg) to be installed.

Dual-mode strategy (documented in docs/database/SCHEMA.md):
  - Local/dev: SQLite per-agent in data/agents/{id}/memory.db
  - Server/Docker/prod: this backend, single DB, indexed by agent_id
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, List, Optional

from gen_agent.interfaces.memory_protocol import MemoryQuery, MemoryRecord

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id     TEXT PRIMARY KEY,
    agent_id      TEXT NOT NULL,
    content       TEXT NOT NULL,
    memory_type   TEXT NOT NULL,
    importance    FLOAT NOT NULL,
    created_at    FLOAT NOT NULL,
    last_accessed FLOAT NOT NULL,
    extra         JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_type  ON memories(agent_id, memory_type);
"""


class PostgresMemoryBackend:
    """
    Thread-safe PostgreSQL backend.

    ponytail: uses a simple connection per thread via threading.local.
    For high concurrency, swap with psycopg2.pool.ThreadedConnectionPool.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._local = threading.local()
        self._init_schema()

    def _conn(self) -> Any:
        import psycopg2
        import psycopg2.extras
        conn = getattr(self._local, "conn", None)
        if conn is None or conn.closed:
            conn = psycopg2.connect(self._dsn)
            conn.autocommit = False
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        conn = self._conn()
        with conn.cursor() as cur:
            for stmt in _CREATE_TABLE.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        conn.commit()

    def store(self, record: MemoryRecord) -> None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memories
                    (memory_id, agent_id, content, memory_type, importance,
                     created_at, last_accessed, extra)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (memory_id) DO UPDATE SET
                    content       = EXCLUDED.content,
                    importance    = EXCLUDED.importance,
                    last_accessed = EXCLUDED.last_accessed,
                    extra         = EXCLUDED.extra
                """,
                (
                    record.memory_id,
                    record.agent_id,
                    record.content,
                    record.memory_type,
                    record.importance,
                    record.created_at,
                    record.last_accessed,
                    json.dumps(record.extra),
                ),
            )
        conn.commit()

    def retrieve(self, query: MemoryQuery) -> List[MemoryRecord]:
        if not query.memory_types:
            return []
        placeholders = ", ".join(f"%s" for _ in query.memory_types)
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT memory_id, agent_id, content, memory_type, importance,
                       created_at, last_accessed, extra
                FROM memories
                WHERE agent_id = %s
                  AND memory_type IN ({placeholders})
                  AND importance >= %s
                ORDER BY last_accessed DESC
                LIMIT %s
                """,
                (query.agent_id, *query.memory_types, query.min_importance, query.top_k),
            )
            rows = cur.fetchall()
        return [
            MemoryRecord(
                memory_id=r[0],
                agent_id=r[1],
                content=r[2],
                memory_type=r[3],
                importance=float(r[4]),
                created_at=float(r[5]),
                last_accessed=float(r[6]),
                extra=r[7] if isinstance(r[7], dict) else json.loads(r[7] or "{}"),
            )
            for r in rows
        ]

    def touch(self, memory_id: str) -> None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE memories SET last_accessed = %s WHERE memory_id = %s",
                (time.time(), memory_id),
            )
        conn.commit()

    def delete(self, memory_id: str) -> None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM memories WHERE memory_id = %s", (memory_id,))
        conn.commit()

    def count(self, agent_id: Optional[str] = None) -> int:
        conn = self._conn()
        with conn.cursor() as cur:
            if agent_id:
                cur.execute("SELECT COUNT(*) FROM memories WHERE agent_id = %s", (agent_id,))
            else:
                cur.execute("SELECT COUNT(*) FROM memories")
            return cur.fetchone()[0]
