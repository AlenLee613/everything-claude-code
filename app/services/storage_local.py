import sqlite3
import json
import time
import os
from typing import Optional, Dict, Any, Tuple
from contextlib import contextmanager
from app.config import settings
from app.services.storage_interface import StorageBackend

class LocalStorage(StorageBackend):
    def __init__(self):
        self.db_path = settings.LOCAL_STORAGE_PATH
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        try:
            with self._connect() as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ephemeral_keys (
                        key_id TEXT PRIMARY KEY,
                        info_json TEXT NOT NULL,
                        remaining INTEGER NOT NULL,
                        expires_at REAL NOT NULL
                    )
                """)
                conn.commit()
        except Exception as e:
            # print(f"Error initializing DB: {e}")
            pass

    def create_key(self, key_id: str, info: Dict[str, Any], ttl_seconds: int) -> None:
        now = time.time()
        expires_at = now + ttl_seconds
        clean_info = {k: str(v) for k, v in info.items()}
        initial_remaining = int(info.get("max_requests", 0))
        
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ephemeral_keys (key_id, info_json, remaining, expires_at) VALUES (?, ?, ?, ?)",
                (key_id, json.dumps(clean_info), initial_remaining, expires_at)
            )
            conn.commit()

    def get_key_status(self, key_id: str) -> Optional[Tuple[Dict[str, str], int]]:
        now = time.time()
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT info_json, remaining, expires_at FROM ephemeral_keys WHERE key_id = ?",
                (key_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            info_json, remaining, expires_at = row
            
            if now > expires_at:
                try:
                    conn.execute("DELETE FROM ephemeral_keys WHERE key_id = ?", (key_id,))
                    conn.commit()
                except:
                    pass
                return None
            
            return json.loads(info_json), remaining

    def decrement_remaining(self, key_id: str) -> int:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                cursor = conn.execute("SELECT remaining FROM ephemeral_keys WHERE key_id = ?", (key_id,))
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return -1
                
                current = row[0]
                new_val = current - 1
                
                conn.execute("UPDATE ephemeral_keys SET remaining = ? WHERE key_id = ?", (new_val, key_id))
                conn.commit()
                return new_val
            except Exception:
                conn.rollback()
                raise

    def delete_key(self, key_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM ephemeral_keys WHERE key_id = ?", (key_id,))
            conn.commit()

    def exists(self, key_id: str) -> bool:
        now = time.time()
        with self._connect() as conn:
            cursor = conn.execute("SELECT expires_at FROM ephemeral_keys WHERE key_id = ?", (key_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            if now > row[0]:
                try:
                    conn.execute("DELETE FROM ephemeral_keys WHERE key_id = ?", (key_id,))
                    conn.commit()
                except:
                    pass
                return False
                
            return True
