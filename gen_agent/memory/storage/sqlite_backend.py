"""
SQLite persistence backend for the memory system.

Thin wrapper: schema init, store, retrieve.
No business logic here — that lives in MemoryManager.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from gen_agent.interfaces.memory_protocol import MemoryQuery, MemoryRecord

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id    TEXT PRIMARY KEY,
    agent_id     TEXT NOT NULL,
    content      TEXT NOT NULL,
    memory_type  TEXT NOT NULL,
    importance   REAL NOT NULL,
    created_at   REAL NOT NULL,
    last_accessed REAL NOT NULL,
    extra        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_type  ON memories(agent_id, memory_type);
"""


class SQLiteMemoryBackend:
    """Thread-safe SQLite backend. One connection per thread via threading.local."""

    def __init__(self, db_path: str = "gen_agent.db") -> None:
        # ponytail: :memory: must not be resolved to an absolute filesystem path
        self._db_path = db_path if db_path == ":memory:" else str(Path(db_path).resolve())
        self._local = threading.local()
        self._init_schema()

    # ------------------------------------------------------------------
    # Internal connection management
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        if not getattr(self._local, "conn", None):
            self._local.conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_schema(self) -> None:
        self._conn().executescript(_CREATE_TABLE)
        self._conn().commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, record: MemoryRecord) -> None:
        self._conn().execute(
            """
            INSERT OR REPLACE INTO memories
                (memory_id, agent_id, content, memory_type, importance,
                 created_at, last_accessed, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        self._conn().commit()

    def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        placeholders = ", ".join("?" * len(query.memory_types))
        rows = self._conn().execute(
            f"""
            SELECT * FROM memories
            WHERE agent_id = ?
              AND memory_type IN ({placeholders})
              AND importance >= ?
            ORDER BY last_accessed DESC
            LIMIT ?
            """,
            (query.agent_id, *query.memory_types, query.min_importance, query.top_k),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def touch(self, memory_id: str) -> None:
        self._conn().execute(
            "UPDATE memories SET last_accessed = ? WHERE memory_id = ?",
            (time.time(), memory_id),
        )
        self._conn().commit()

    def delete(self, memory_id: str) -> None:
        self._conn().execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
        self._conn().commit()

    def count(self, agent_id: str | None = None) -> int:
        if agent_id:
            return self._conn().execute(
                "SELECT COUNT(*) FROM memories WHERE agent_id = ?", (agent_id,)
            ).fetchone()[0]
        return self._conn().execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            memory_id=row["memory_id"],
            agent_id=row["agent_id"],
            content=row["content"],
            memory_type=row["memory_type"],
            importance=row["importance"],
            created_at=row["created_at"],
            last_accessed=row["last_accessed"],
            extra=json.loads(row["extra"]),
        )
