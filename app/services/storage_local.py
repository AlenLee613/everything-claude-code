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
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS usage_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        key_id TEXT NOT NULL,
                        model TEXT NOT NULL,
                        tokens INTEGER NOT NULL,
                        cost REAL NOT NULL,
                        request_count INTEGER DEFAULT 1
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_logs(timestamp)")
                
                # Table for rate limiting
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rate_limits (
                        key_id TEXT PRIMARY KEY,
                        rpm INTEGER NOT NULL
                    )
                """)
                # Table for request timestamps (sliding window / fixed window)
                # For simplicity in SQLite, we can use a table storing recent timestamps per key
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS request_timestamps (
                        key_id TEXT,
                        timestamp REAL,
                        expiration REAL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_req_ts_key ON request_timestamps(key_id, timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_req_ts_exp ON request_timestamps(expiration)")
                
                # Table for attribution logs
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS attribution_logs (
                        request_id TEXT PRIMARY KEY,
                        token_id TEXT NOT NULL,
                        model TEXT NOT NULL,
                        endpoint TEXT NOT NULL,
                        status_code INTEGER NOT NULL,
                        latency_ms REAL NOT NULL,
                        total_tokens INTEGER DEFAULT 0,
                        inflight_concurrency INTEGER NOT NULL,
                        created_at REAL NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_attr_created ON attribution_logs(created_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_attr_token ON attribution_logs(token_id)")

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

    def update_key_policy(self, key_id: str, policy: Dict[str, Any]) -> None:
        with self._connect() as conn:
            cursor = conn.execute("SELECT info_json FROM ephemeral_keys WHERE key_id = ?", (key_id,))
            row = cursor.fetchone()
            if not row:
                return # Key not found
            
            info = json.loads(row[0])
            info["ip_policy"] = policy
            
            conn.execute(
                "UPDATE ephemeral_keys SET info_json = ? WHERE key_id = ?", 
                (json.dumps(info), key_id)
            )
            conn.commit()

    def log_usage(self, key_id: str, usage_data: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO usage_logs (timestamp, key_id, model, tokens, cost, request_count) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    usage_data["timestamp"],
                    key_id,
                    usage_data.get("model", "unknown"),
                    int(usage_data.get("tokens", 0)),
                    float(usage_data.get("cost", 0.0)),
                    1
                )
            )
            conn.commit()

    def get_usage_logs(self, start_ts: float, end_ts: float) -> list[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT timestamp, key_id, model, tokens, cost, request_count FROM usage_logs WHERE timestamp >= ? AND timestamp < ?",
                (start_ts, end_ts)
            )
            rows = cursor.fetchall()
            return [
                {
                    "timestamp": row[0],
                    "key_id": row[1],
                    "model": row[2],
                    "tokens": row[3],
                    "cost": row[4],
                    "request_count": row[5]
                }
                for row in rows
            ]

    def set_key_rpm(self, key_id: str, rpm: int) -> None:
        """
        Set RPM configuration for a key.
        Since we store config in Info JSON, we update that.
        """
        with self._connect() as conn:
            cursor = conn.execute("SELECT info_json FROM ephemeral_keys WHERE key_id = ?", (key_id,))
            row = cursor.fetchone()
            if not row:
                return # Key not found
            
            info = json.loads(row[0])
            info["rpm"] = rpm
            
            conn.execute(
                "UPDATE ephemeral_keys SET info_json = ? WHERE key_id = ?", 
                (json.dumps(info), key_id)
            )
            conn.commit()

    def check_rate_limit(self, key_id: str, rpm: int) -> bool:
        """
        Check rate limit using a sliding window (1 minute).
        
        Args:
            key_id: The key to check
            rpm: The RPM limit (passed from info or default)
            
        Returns:
            True if allowed, False if limit exceeded
        """
        now = time.time()
        window_start = now - 60
        
        # We can optimize by cleaning up old records first (or periodically)
        # But for correctness, we just count records in the last minute.
        
        with self._connect() as conn:
            # 1. Clean up old records (optional but good for performance)
            # Make it probabilistic or just do it? SQLite is fast enough for small loads.
            conn.execute("DELETE FROM request_timestamps WHERE expiration < ?", (now,))
            
            # 2. Count requests in window for this key
            cursor = conn.execute(
                "SELECT COUNT(*) FROM request_timestamps WHERE key_id = ? AND timestamp > ?",
                (key_id, window_start)
            )
            count = cursor.fetchone()[0]
            
            if count >= rpm:
                conn.commit()
                return False
            
            # 3. Add current request
            expiration = now + 60
            conn.execute(
                "INSERT INTO request_timestamps (key_id, timestamp, expiration) VALUES (?, ?, ?)",
                (key_id, now, expiration)
            )
            conn.commit()
            return True

    def log_attribution(self, log_entry: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO attribution_logs (
                    request_id, token_id, model, endpoint, status_code, 
                    latency_ms, total_tokens, inflight_concurrency, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_entry["request_id"],
                log_entry["token_id"],
                log_entry["model"],
                log_entry["endpoint"],
                log_entry["status_code"],
                log_entry["latency_ms"],
                log_entry.get("total_tokens", 0),
                log_entry["inflight_concurrency"],
                log_entry["created_at"]
            ))
            conn.commit()

    def get_attribution_logs(self, filters: Dict[str, Any], page: int = 1, page_size: int = 20) -> Tuple[list[Dict[str, Any]], int]:
        query = "SELECT * FROM attribution_logs WHERE 1=1"
        params = []
        
        if "start" in filters and filters["start"]:
            query += " AND created_at >= ?"
            params.append(float(filters["start"]))
        if "end" in filters and filters["end"]:
            query += " AND created_at <= ?"
            params.append(float(filters["end"]))
        if "token_id" in filters and filters["token_id"]:
            query += " AND token_id = ?"
            params.append(filters["token_id"])
        if "model" in filters and filters["model"]:
            query += " AND model = ?"
            params.append(filters["model"])
        if "status" in filters and filters["status"]:
            try:
                status_code = int(filters["status"])
                query += " AND status_code = ?"
                params.append(status_code)
            except ValueError:
                pass
        
        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        
        with self._connect() as conn:
            cursor = conn.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Get data
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.append(page_size)
            params.append((page - 1) * page_size)
            
            cursor = conn.execute(query, params)
            columns = [col[0] for col in cursor.description]
            logs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return logs, total_count

