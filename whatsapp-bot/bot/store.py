"""SQLite storage: conversation history, processed message ids, handoffs, orders/bookings."""

import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wa_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    text TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_wa ON messages (wa_id, id);
CREATE TABLE IF NOT EXISTS processed (msg_id TEXT PRIMARY KEY, ts REAL NOT NULL);
CREATE TABLE IF NOT EXISTS handoffs (wa_id TEXT PRIMARY KEY, reason TEXT, ts REAL NOT NULL);
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wa_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    customer_name TEXT,
    details TEXT NOT NULL,
    requested_time TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    ts REAL NOT NULL
);
"""


class Store:
    def __init__(self, path: str):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(SCHEMA)

    def _exec(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._db.execute(sql, args)
            self._db.commit()
            return cur

    def _query(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    # --- dedupe: Meta retries webhooks, so each message id is handled once ---
    def mark_processed(self, msg_id: str) -> bool:
        """Return True the first time a message id is seen."""
        try:
            self._exec("INSERT INTO processed (msg_id, ts) VALUES (?, ?)", (msg_id, time.time()))
            return True
        except sqlite3.IntegrityError:
            return False

    # --- conversation history ---
    def add_message(self, wa_id: str, role: str, text: str) -> None:
        self._exec(
            "INSERT INTO messages (wa_id, role, text, ts) VALUES (?, ?, ?, ?)",
            (wa_id, role, text, time.time()),
        )

    def recent_messages(self, wa_id: str, limit: int) -> list[dict]:
        rows = self._query(
            "SELECT role, text FROM messages WHERE wa_id = ? ORDER BY id DESC LIMIT ?",
            (wa_id, limit),
        )
        history = [{"role": r["role"], "content": r["text"]} for r in reversed(rows)]
        # The API needs strictly alternating turns that start with the user.
        merged: list[dict] = []
        for msg in history:
            if merged and merged[-1]["role"] == msg["role"]:
                merged[-1]["content"] += "\n" + msg["content"]
            else:
                merged.append(dict(msg))
        while merged and merged[0]["role"] != "user":
            merged.pop(0)
        return merged

    # --- human handoff ---
    def set_handoff(self, wa_id: str, reason: str) -> None:
        self._exec(
            "INSERT OR REPLACE INTO handoffs (wa_id, reason, ts) VALUES (?, ?, ?)",
            (wa_id, reason, time.time()),
        )

    def clear_handoff(self, wa_id: str) -> bool:
        return self._exec("DELETE FROM handoffs WHERE wa_id = ?", (wa_id,)).rowcount > 0

    def is_handed_off(self, wa_id: str) -> bool:
        return bool(self._query("SELECT 1 FROM handoffs WHERE wa_id = ?", (wa_id,)))

    def list_handoffs(self) -> list[dict]:
        return [dict(r) for r in self._query("SELECT * FROM handoffs ORDER BY ts DESC")]

    # --- orders / bookings ---
    def add_request(self, wa_id: str, kind: str, customer_name: str, details: str,
                    requested_time: str) -> int:
        cur = self._exec(
            "INSERT INTO requests (wa_id, kind, customer_name, details, requested_time, ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (wa_id, kind, customer_name, details, requested_time, time.time()),
        )
        return int(cur.lastrowid)

    def list_requests(self, status: str | None = None) -> list[dict]:
        if status:
            rows = self._query("SELECT * FROM requests WHERE status = ? ORDER BY id DESC", (status,))
        else:
            rows = self._query("SELECT * FROM requests ORDER BY id DESC")
        return [dict(r) for r in rows]

    def set_request_status(self, request_id: int, status: str) -> bool:
        return self._exec(
            "UPDATE requests SET status = ? WHERE id = ?", (status, request_id)
        ).rowcount > 0
