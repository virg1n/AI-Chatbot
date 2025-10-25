import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from backend.faiss_index import DEFAULT_DATA_DIR  # reuse your data dir

DB_PATH = os.path.join(DEFAULT_DATA_DIR, "people.db")

# Ensure data dir exists
os.makedirs(DEFAULT_DATA_DIR, exist_ok=True)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS people (
    phone_number TEXT PRIMARY KEY,
    first_name TEXT,
    last_name  TEXT,
    age        INTEGER,
    relation   TEXT,
    memory_about TEXT,
    last_conversation TEXT,
    stories_for TEXT,
    questions_for TEXT,
    updated_at TEXT
);
"""

APPENDABLE_FIELDS = {"memory_about", "last_conversation", "stories_for", "questions_for"}
SETTABLE_FIELDS = {"first_name", "last_name", "relation", "age"}.union(APPENDABLE_FIELDS)

def _connect() -> sqlite3.Connection:
    # Create a fresh connection per call (safe for threaded Flask)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db() -> None:
    with _connect() as con:
        con.execute(SCHEMA_SQL)
        con.commit()

def normalize_phone(p: str) -> str:
    # Keep + and digits; you can adjust to your needs
    p = (p or "").strip()
    if p.startswith("+"):
        return "+" + "".join(ch for ch in p[1:] if ch.isdigit())
    return "".join(ch for ch in p if ch.isdigit())

def append_text(existing: Optional[str], addition: str) -> str:
    if not addition:
        return existing or ""
    if not existing:
        return addition
    return f"{existing}\n{addition}"

def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def get_person(phone_number: str) -> Optional[Dict[str, Any]]:
    phone = normalize_phone(phone_number)
    with _connect() as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT * FROM people WHERE phone_number = ?",
            (phone,),
        ).fetchone()
        return dict(row) if row else None

def _insert_empty_person(con: sqlite3.Connection, phone: str) -> None:
    con.execute(
        """INSERT OR IGNORE INTO people (phone_number, updated_at)
           VALUES (?, ?)""",
        (phone, _now_iso()),
    )

def create_or_update_person(phone_number: str, payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    - If person exists: append or set fields based on rules
    - If not: create person, then apply same logic
    Returns (action, person_dict) where action is "created" or "updated"
    """
    phone = normalize_phone(phone_number)
    if not phone:
        raise ValueError("phone_number is required")

    # Filter to known fields
    updates = {k: v for k, v in payload.items() if k in SETTABLE_FIELDS}

    # Normalize some types
    if "age" in updates:
        try:
            updates["age"] = int(updates["age"])
        except Exception:
            # If not an int, drop it silently (or raise if you prefer)
            updates.pop("age", None)

    with _connect() as con:
        con.row_factory = sqlite3.Row
        existing = con.execute(
            "SELECT * FROM people WHERE phone_number = ?", (phone,)
        ).fetchone()

        action = "updated" if existing else "created"
        if not existing:
            _insert_empty_person(con, phone)
            existing_dict = {"phone_number": phone}
        else:
            existing_dict = dict(existing)

        # Build new values
        new_values: Dict[str, Any] = {}
        for field, value in updates.items():
            if field in APPENDABLE_FIELDS:
                # Accept list or str; convert list to bullet lines
                if isinstance(value, list):
                    value = "\n".join(f"- {str(x)}" for x in value)
                # Optional: timestamp each appended chunk for traceability
                stamped = f"[{_now_iso()}]\n{value}"
                new_values[field] = append_text(existing_dict.get(field), stamped)
            else:
                # set/overwrite (first_name, last_name, relation, age)
                new_values[field] = value

        # Always bump updated_at
        new_values["updated_at"] = _now_iso()

        if new_values:
            # Prepare dynamic SQL
            assignments = ", ".join(f"{k} = ?" for k in new_values.keys())
            params = list(new_values.values()) + [phone]
            con.execute(f"UPDATE people SET {assignments} WHERE phone_number = ?", params)
            con.commit()

        # Return full person
        person = con.execute(
            "SELECT * FROM people WHERE phone_number = ?", (phone,)
        ).fetchone()
        return action, dict(person)
