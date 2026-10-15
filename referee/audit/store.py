import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nacl.signing import SigningKey

from contracts.audit import AuditEntry, Checkpoint
from contracts.canonical import GENESIS, canonical_json, entry_hash
from contracts.crypto.sign import sign_checkpoint, sign_entry_hash


class AuditStore:
    def __init__(self, db_path: str | None = None, signing_key_hex: str | None = None):
        if db_path is None:
            env_db = os.environ.get("AUDIT_DB_PATH")
            if env_db:
                db_path = env_db
            elif Path("/data").exists() and os.access("/data", os.W_OK):
                db_path = "/data/audit.db"
            else:
                db_path = "/tmp/sra_audit.db"
        self.db_path = db_path

        # Ensure parent directory exists if using local filesystem
        db_parent = Path(self.db_path).parent
        if str(db_parent) != "" and str(db_parent) != ".":
            try:
                db_parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

        if signing_key_hex is None:
            signing_key_hex = self._read_signing_key()
        self.signing_key_bytes = bytes.fromhex(signing_key_hex)
        self.signing_key = SigningKey(self.signing_key_bytes)
        self.verify_key_hex = self.signing_key.verify_key.encode().hex()

        self._lock = threading.Lock()
        self._init_db()

    def _read_signing_key(self) -> str:
        key = os.environ.get("AUDIT_SIGNING_KEY")
        if key:
            return key.strip()
        for p in ["/run/secrets/audit_signing_key", "secrets/audit_signing_key.txt"]:
            path = Path(p)
            if path.exists():
                return path.read_text().strip()
        # Fallback for dev/testing if no secret mounted: 32 bytes of 0x01
        return "01" * 32

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS entries (
                        seq INTEGER PRIMARY KEY,
                        entry_hash TEXT NOT NULL,
                        body TEXT NOT NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS no_update
                    BEFORE UPDATE ON entries
                    BEGIN
                        SELECT RAISE(ABORT, 'append-only');
                    END;
                    """
                )
                cursor.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS no_delete
                    BEFORE DELETE ON entries
                    BEGIN
                        SELECT RAISE(ABORT, 'append-only');
                    END;
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def head(self) -> tuple[int, str, dict[str, Any] | None]:
        """Return (latest_seq, head_hash, latest_entry_dict)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT seq, entry_hash, body FROM entries ORDER BY seq DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return 0, GENESIS, None
            import json

            return row[0], row[1], json.loads(row[2])
        finally:
            conn.close()

    def append(self, fields: dict[str, Any]) -> AuditEntry:
        """Append an audit entry under lock, building hash chain and signature."""
        with self._lock:
            count, prev_hash, _ = self.head()
            next_seq = count + 1
            ts = datetime.now(timezone.utc).isoformat()

            entry_dict = {
                **fields,
                "seq": next_seq,
                "ts": ts,
                "prev_hash": prev_hash,
            }

            h = entry_hash(prev_hash, entry_dict)
            sig = sign_entry_hash(self.signing_key_bytes, h)

            entry = AuditEntry(**entry_dict, entry_hash=h, sig=sig)
            body_json = canonical_json(entry.model_dump()).decode("utf-8")

            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO entries(seq, entry_hash, body) VALUES (?, ?, ?)",
                    (next_seq, h, body_json),
                )
                conn.commit()
            finally:
                conn.close()

            return entry

    def export(self) -> list[dict[str, Any]]:
        """Return all entries in order of sequence."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT body FROM entries ORDER BY seq ASC")
            import json

            return [json.loads(row[0]) for row in cursor.fetchall()]
        finally:
            conn.close()

    def checkpoint(self, round_id: str) -> Checkpoint:
        """Produce signed checkpoint for current state."""
        with self._lock:
            count, head_hash, _ = self.head()
            sig = sign_checkpoint(self.signing_key_bytes, round_id, count, head_hash)
            return Checkpoint(
                round_id=round_id,
                count=count,
                head_hash=head_hash,
                sig=sig,
            )
