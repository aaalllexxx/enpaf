"""
ENPAF Core — Local Storage
SQLite-based key-value storage with collections support.
"""

import json
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional


class Storage:
    """
    Persistent key-value storage backed by SQLite.
    Works on both dev (desktop) and Android.
    
    Usage:
        storage = Storage("data/app.db")
        storage.set("theme", "dark")
        theme = storage.get("theme")  # "dark"
        
        # Collections
        storage.collection("users").add({"name": "Alex", "age": 25})
        users = storage.collection("users").all()
    """

    def __init__(self, db_path: str = "enpaf_data.db"):
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            os.makedirs(os.path.dirname(self._db_path) if os.path.dirname(self._db_path) else ".", exist_ok=True)
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'string',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_collections_name 
            ON collections(collection)
        """)
        conn.commit()

    def set(self, key: str, value: Any) -> None:
        """Set a key-value pair."""
        conn = self._get_conn()
        value_type = type(value).__name__
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value, ensure_ascii=False)
            value_type = "json"
        else:
            serialized = str(value)

        conn.execute(
            """INSERT INTO kv_store (key, value, type, updated_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET 
               value=excluded.value, type=excluded.type, updated_at=CURRENT_TIMESTAMP""",
            (key, serialized, value_type),
        )
        conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT value, type FROM kv_store WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if row is None:
            return default

        value, value_type = row
        return self._deserialize(value, value_type)

    def delete(self, key: str) -> bool:
        """Delete a key-value pair. Returns True if key existed."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM kv_store WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT 1 FROM kv_store WHERE key = ?", (key,)
        )
        return cursor.fetchone() is not None

    def keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all keys, optionally filtered by LIKE pattern."""
        conn = self._get_conn()
        if pattern:
            cursor = conn.execute(
                "SELECT key FROM kv_store WHERE key LIKE ?", (pattern,)
            )
        else:
            cursor = conn.execute("SELECT key FROM kv_store")
        return [row[0] for row in cursor.fetchall()]

    def all(self) -> Dict[str, Any]:
        """Get all key-value pairs."""
        conn = self._get_conn()
        cursor = conn.execute("SELECT key, value, type FROM kv_store")
        result = {}
        for key, value, value_type in cursor.fetchall():
            result[key] = self._deserialize(value, value_type)
        return result

    def clear(self) -> None:
        """Delete all key-value pairs."""
        conn = self._get_conn()
        conn.execute("DELETE FROM kv_store")
        conn.commit()

    def collection(self, name: str) -> "Collection":
        """Get a named collection for structured data."""
        return Collection(self, name)

    def _deserialize(self, value: str, value_type: str) -> Any:
        """Deserialize a stored value to its original type."""
        if value_type == "json":
            return json.loads(value)
        elif value_type == "int":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type == "bool":
            return value.lower() in ("true", "1", "yes")
        elif value_type == "NoneType":
            return None
        return value

    def close(self):
        """Close the database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


class Collection:
    """
    A named collection within the storage (like a simple document store).
    
    Usage:
        users = storage.collection("users")
        users.add({"name": "Alex", "age": 25})
        all_users = users.all()
        user = users.find_one({"name": "Alex"})
    """

    def __init__(self, storage: Storage, name: str):
        self._storage = storage
        self._name = name

    def add(self, data: dict) -> int:
        """Add a document to the collection. Returns the document ID."""
        conn = self._storage._get_conn()
        cursor = conn.execute(
            "INSERT INTO collections (collection, data) VALUES (?, ?)",
            (self._name, json.dumps(data, ensure_ascii=False)),
        )
        conn.commit()
        return cursor.lastrowid

    def all(self) -> List[Dict[str, Any]]:
        """Get all documents in the collection."""
        conn = self._storage._get_conn()
        cursor = conn.execute(
            "SELECT id, data, created_at FROM collections WHERE collection = ? ORDER BY id",
            (self._name,),
        )
        results = []
        for row_id, data, created_at in cursor.fetchall():
            doc = json.loads(data)
            doc["_id"] = row_id
            doc["_created_at"] = created_at
            results.append(doc)
        return results

    def find(self, query: dict) -> List[Dict[str, Any]]:
        """Find documents matching a query (simple field matching)."""
        all_docs = self.all()
        return [
            doc for doc in all_docs
            if all(doc.get(k) == v for k, v in query.items())
        ]

    def find_one(self, query: dict) -> Optional[Dict[str, Any]]:
        """Find the first document matching a query."""
        results = self.find(query)
        return results[0] if results else None

    def update(self, doc_id: int, data: dict) -> bool:
        """Update a document by ID."""
        conn = self._storage._get_conn()
        cursor = conn.execute(
            """UPDATE collections SET data = ?, updated_at = CURRENT_TIMESTAMP 
               WHERE id = ? AND collection = ?""",
            (json.dumps(data, ensure_ascii=False), doc_id, self._name),
        )
        conn.commit()
        return cursor.rowcount > 0

    def delete(self, doc_id: int) -> bool:
        """Delete a document by ID."""
        conn = self._storage._get_conn()
        cursor = conn.execute(
            "DELETE FROM collections WHERE id = ? AND collection = ?",
            (doc_id, self._name),
        )
        conn.commit()
        return cursor.rowcount > 0

    def count(self) -> int:
        """Count documents in the collection."""
        conn = self._storage._get_conn()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM collections WHERE collection = ?",
            (self._name,),
        )
        return cursor.fetchone()[0]

    def clear(self) -> None:
        """Delete all documents in the collection."""
        conn = self._storage._get_conn()
        conn.execute(
            "DELETE FROM collections WHERE collection = ?", (self._name,)
        )
        conn.commit()
