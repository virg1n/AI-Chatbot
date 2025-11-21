import os
import sqlite3
import faiss
import numpy as np
from typing import List, Tuple, Optional

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))

DEFAULT_IMAGES_DIR = str(DEFAULT_DATA_DIR / "images")
DEFAULT_INDEX_PATH = str(DEFAULT_DATA_DIR / "index.faiss")
DEFAULT_META_DB     = str(DEFAULT_DATA_DIR / "meta.db")

def _ensure_dirs():
    Path(DEFAULT_DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(DEFAULT_IMAGES_DIR).mkdir(parents=True, exist_ok=True)

def _ensure_column(cur: sqlite3.Cursor, table: str, name: str, col_type: str) -> None:
    """
    Add a column if it does not exist. Safe to call repeatedly.
    """
    cur.execute(f"PRAGMA table_info({table})")
    cols = {row[1] for row in cur.fetchall()}
    if name not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}")

# DEFAULT_DATA_DIR = os.path.join(r"", "data") #os.environ.get("DATA_DIR", "/var/www/mindxium/data")
# DEFAULT_IMAGES_DIR = os.path.join(DEFAULT_DATA_DIR, "images")
# DEFAULT_INDEX_PATH = os.path.join(DEFAULT_DATA_DIR, "index.faiss")
# DEFAULT_META_DB = os.path.join(DEFAULT_DATA_DIR, "meta.db")


# def _ensure_dirs():
#     os.makedirs(DEFAULT_DATA_DIR, exist_ok=True)
#     os.makedirs(DEFAULT_IMAGES_DIR, exist_ok=True)


class ImageVectorIndex:
    """
    A thin wrapper around a cosine-similarity FAISS index with an SQLite metadata store.
    Vectors are stored L2-normalized and searched with inner product (cosine).
    """
    def __init__(
        self,
        dim: int,
        index_path: str = DEFAULT_INDEX_PATH,
        meta_db_path: str = DEFAULT_META_DB,
    ):
        _ensure_dirs()
        self.dim = dim
        self.index_path = index_path
        self.meta_db_path = meta_db_path

        self.conn = sqlite3.connect(self.meta_db_path, check_same_thread=False)
        self._init_meta()

        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            # sanity check for dimension
            if self.index.d != dim:
                raise ValueError(
                    f"Existing index dim={self.index.d} does not match requested dim={dim}"
                )
        else:
            # Cosine similarity = inner product with normalized vectors
            self.index = faiss.IndexFlatIP(dim)

        # We maintain our own mapping ID <-> row order using SQLite IDs table.
        # We’ll keep FAISS ids implicit (row order) and store a parallel SQLite table
        # with (faiss_rowid INTEGER PRIMARY KEY AUTOINCREMENT, ext_id TEXT UNIQUE, path TEXT).
        # When we add vectors, we append rows in the same order.
        # To keep things consistent across restarts, we will rebuild alignment
        # using stored count check.
        self._validate_alignment()

    def _init_meta(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS images (
                faiss_rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                ext_id TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                caption TEXT,
                user_caption TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        # Ensure new columns exist for existing deployments
        _ensure_column(cur, "images", "caption", "TEXT")
        _ensure_column(cur, "images", "user_caption", "TEXT")
        _ensure_column(cur, "images", "is_active", "INTEGER DEFAULT 1")
        self.conn.commit()

    def _validate_alignment(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(1) FROM images")
        (meta_count,) = cur.fetchone()
        index_count = self.index.ntotal
        if meta_count != index_count:
            # If mismatch: you can resolve by rebuilding the index externally.
            # We fail loudly to prevent corrupted results.
            raise RuntimeError(
                f"Metadata count ({meta_count}) != FAISS vectors ({index_count}). "
                f"Rebuild the index or fix meta.db/index.faiss alignment."
            )

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        # vectors: (N, D)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
        return vectors / norms

    def add(
        self,
        ext_ids: List[str],
        paths: List[str],
        vectors: np.ndarray,
        captions: Optional[List[Optional[str]]] = None,
        user_captions: Optional[List[Optional[str]]] = None,
        actives: Optional[List[int]] = None,
    ):
        """
        Add new vectors with external IDs and file paths.
        ext_ids: list of unique external IDs (e.g., UUIDs)
        paths: list of file paths corresponding to each vector
        vectors: shape (N, D) float32
        """
        assert len(ext_ids) == len(paths) == vectors.shape[0], "Mismatched lengths"
        if captions is None:
            captions = [None] * len(ext_ids)
        if user_captions is None:
            user_captions = [None] * len(ext_ids)
        if actives is None:
            actives = [1] * len(ext_ids)
        assert len(captions) == len(ext_ids)
        assert len(user_captions) == len(ext_ids)
        assert len(actives) == len(ext_ids)

        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32)

        vectors = self._normalize(vectors)
        self.index.add(vectors)

        cur = self.conn.cursor()
        cur.executemany(
            "INSERT INTO images (ext_id, path, caption, user_caption, is_active) VALUES (?, ?, ?, ?, ?)",
            list(zip(ext_ids, paths, captions, user_captions, actives)),
        )
        self.conn.commit()
        self.save()

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, str, float, Optional[str], Optional[str], int]]:
        """
        Search by a single query vector.
        Returns list of (ext_id, path, score, caption, user_caption, is_active) sorted by score desc.
        """
        if query_vector.ndim == 1:
            query_vector = query_vector[None, :]
        if query_vector.dtype != np.float32:
            query_vector = query_vector.astype(np.float32)
        query_vector = self._normalize(query_vector)

        scores, indices = self.index.search(query_vector, top_k)
        idxs = indices[0].tolist()
        scs = scores[0].tolist()

        # Map FAISS row indices to ext_id + path
        placeholders = ",".join("?" for _ in idxs)
        cur = self.conn.cursor()
        cur.execute(
            f"""SELECT faiss_rowid, ext_id, path, caption, user_caption, is_active
                FROM images
                WHERE faiss_rowid IN ({placeholders})""",
            [i + 1 for i in idxs]  # SQLite AUTOINCREMENT starts at 1; FAISS rows start at 0
        )
        rows = {row[0] - 1: (row[1], row[2], row[3], row[4], row[5]) for row in cur.fetchall()}  # map to 0-based

        results = []
        for i, s in zip(idxs, scs):
            if i == -1:
                continue
            ext_id, path, caption, user_caption, is_active = rows.get(i, ("", "", None, None, 1))
            results.append((ext_id, path, float(s), caption, user_caption, int(is_active)))
        return results

    def list_all(self, include_inactive: bool = True) -> List[Tuple[str, str, Optional[str], Optional[str], int]]:
        cur = self.conn.cursor()
        if include_inactive:
            cur.execute("SELECT ext_id, path, caption, user_caption, is_active FROM images ORDER BY faiss_rowid ASC")
        else:
            cur.execute("SELECT ext_id, path, caption, user_caption, is_active FROM images WHERE is_active = 1 ORDER BY faiss_rowid ASC")
        return cur.fetchall()

    def set_user_caption(self, ext_id: str, user_caption: Optional[str]) -> None:
        cur = self.conn.cursor()
        cur.execute("UPDATE images SET user_caption = ? WHERE ext_id = ?", (user_caption, ext_id))
        self.conn.commit()

    def set_active(self, ext_id: str, is_active: int) -> None:
        cur = self.conn.cursor()
        cur.execute("UPDATE images SET is_active = ? WHERE ext_id = ?", (is_active, ext_id))
        self.conn.commit()

    def save(self):
        faiss.write_index(self.index, self.index_path)

    def count(self) -> int:
        return int(self.index.ntotal)

    def get_by_ext_id(self, ext_id: str) -> Optional[Tuple[int, str]]:
        cur = self.conn.cursor()
        cur.execute("SELECT faiss_rowid, path FROM images WHERE ext_id = ?", (ext_id,))
        row = cur.fetchone()
        if not row:
            return None
        faiss_row0 = row[0] - 1
        return faiss_row0, row[1]
