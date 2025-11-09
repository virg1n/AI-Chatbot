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

    Special rules:
      * last_conversation: ALWAYS overwrite (do not append)
      * memory_about: If new text is longer than existing -> overwrite,
                      else append (concatenate with a newline)
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

        def _to_text(val: Any) -> str:
            # Accept list or str; convert list to bullet lines
            if isinstance(val, list):
                return "\n".join(f"- {str(x)}" for x in val)
            return "" if val is None else str(val)

        new_values: Dict[str, Any] = {}
        for field, value in updates.items():
            # --- Special-case rules first ---
            if field == "last_conversation":
                # ALWAYS OVERWRITE
                new_values[field] = _to_text(value)
                continue

            if field == "memory_about":
                # Overwrite if new longer than old; else append
                new_text = _to_text(value)
                old_text = existing_dict.get("memory_about") or ""
                if len(new_text) >= len(old_text):
                    new_values[field] = new_text
                else:
                    # append without timestamp per requirement to "just concatenate"
                    new_values[field] = append_text(old_text, new_text)
                continue

            # --- Default behavior ---
            if field in APPENDABLE_FIELDS:
                # For other appendable fields (e.g., stories_for, questions_for),
                # keep the original timestamped-append behavior.
                stamped = f"[{_now_iso()}]\n{_to_text(value)}"
                new_values[field] = append_text(existing_dict.get(field), stamped)
            else:
                # set/overwrite (first_name, last_name, relation, age)
                new_values[field] = value

        # Always bump updated_at
        new_values["updated_at"] = _now_iso()

        if new_values:
            assignments = ", ".join(f"{k} = ?" for k in new_values.keys())
            params = list(new_values.values()) + [phone]
            con.execute(f"UPDATE people SET {assignments} WHERE phone_number = ?", params)
            con.commit()

        person = con.execute(
            "SELECT * FROM people WHERE phone_number = ?", (phone,)
        ).fetchone()
        return action, dict(person)


def _escape_like(s: str) -> str:
    return s.replace("%", r"\%").replace("_", r"\_")

def get_person_by_name(first_name: str, last_name: str) -> Optional[Dict[str, Any]]:
    """
    Look up a person by name, returning the first one.
    Returns a dict or None.
    """
    fn = (first_name or "").strip()
    ln = (last_name or "").strip()
    if not fn or not ln:
        return None

    with _connect() as con:
        con.row_factory = sqlite3.Row

        row = con.execute(
            """
            SELECT * FROM people
            WHERE lower(first_name) = lower(?)
              AND lower(last_name)  = lower(?)
            ORDER BY datetime(updated_at) DESC
            LIMIT 1
            """,
            (fn, ln),
        ).fetchone()
        if row:
            return dict(row)

        fn_like = f"%{_escape_like(fn)}%"
        ln_like = f"%{_escape_like(ln)}%"
        row = con.execute(
            r"""
            SELECT * FROM people
            WHERE lower(first_name) LIKE lower(?) ESCAPE '\'
              AND lower(last_name)  LIKE lower(?) ESCAPE '\'
            ORDER BY datetime(updated_at) DESC
            LIMIT 1
            """,
            (fn_like, ln_like),
        ).fetchone()
        return dict(row) if row else None