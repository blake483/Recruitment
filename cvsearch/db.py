"""SQLite storage: one row per CV plus a full-text index over the CV text."""

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sqlite3

from . import taxonomy
from .extract import SUPPORTED_EXTENSIONS, ExtractionError, extract_text
from .parser import parse_cv, pattern_for

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY,
    file_hash TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    parsed TEXT NOT NULL DEFAULT '{}',
    overrides TEXT NOT NULL DEFAULT '{}',
    notes TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT ''
);
CREATE VIRTUAL TABLE IF NOT EXISTS cv_fts USING fts5(text, tokenize='porter unicode61');
"""

# Fields you can correct by hand on the candidate page.
EDITABLE = ("name", "email", "phone", "years_experience", "primary_location", "sectors", "current_role")


class Store:
    def __init__(self, data_dir):
        self.data_dir = os.path.abspath(data_dir)
        self.files_dir = os.path.join(self.data_dir, "cvs")
        os.makedirs(self.files_dir, exist_ok=True)
        self.conn = sqlite3.connect(os.path.join(self.data_dir, "cvsearch.db"), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # ------------------------------------------------------------------ write

    def add_file(self, path, original_name=None):
        """Import one CV file. Returns (status, candidate_id_or_None, message).

        status is one of "added", "duplicate", "unsupported", "error".
        """
        original_name = original_name or os.path.basename(path)
        ext = os.path.splitext(original_name)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return "unsupported", None, f"{ext or 'no extension'} is not a CV format"
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        existing = self.conn.execute("SELECT id FROM candidates WHERE file_hash=?", (digest,)).fetchone()
        if existing:
            return "duplicate", existing["id"], "already in database"

        stored_name = digest[:32] + ext
        stored_path = os.path.join(self.files_dir, stored_name)
        shutil.copyfile(path, stored_path)
        error = ""
        try:
            text = extract_text(stored_path)
        except ExtractionError as e:
            text, error = "", str(e)
        if not error and len(text.strip()) < 50:
            error = "Almost no text found - probably a scanned image PDF (needs OCR)."

        parsed = parse_cv(text, original_name)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO candidates (file_hash, filename, stored_name, uploaded_at, text, parsed, error) "
                "VALUES (?,?,?,?,?,?,?)",
                (digest, original_name, stored_name, dt.datetime.now().isoformat(timespec="seconds"),
                 text, json.dumps(parsed), error),
            )
            self.conn.execute("INSERT INTO cv_fts (rowid, text) VALUES (?, ?)", (cur.lastrowid, text))
        return "added", cur.lastrowid, error or "ok"

    def reparse_all(self):
        """Re-run the parser on every stored CV (after editing taxonomy.py)."""
        rows = self.conn.execute("SELECT id, text, filename FROM candidates").fetchall()
        with self.conn:
            for r in rows:
                self.conn.execute("UPDATE candidates SET parsed=? WHERE id=?",
                                  (json.dumps(parse_cv(r["text"], r["filename"])), r["id"]))
        return len(rows)

    def update(self, cid, overrides, notes):
        with self.conn:
            self.conn.execute("UPDATE candidates SET overrides=?, notes=? WHERE id=?",
                              (json.dumps(overrides), notes, cid))

    def delete(self, cid):
        row = self.conn.execute("SELECT stored_name FROM candidates WHERE id=?", (cid,)).fetchone()
        if not row:
            return
        with self.conn:
            self.conn.execute("DELETE FROM candidates WHERE id=?", (cid,))
            self.conn.execute("DELETE FROM cv_fts WHERE rowid=?", (cid,))
        try:
            os.remove(os.path.join(self.files_dir, row["stored_name"]))
        except FileNotFoundError:
            pass

    # ------------------------------------------------------------------ read

    @staticmethod
    def _candidate(row, with_text=False):
        c = json.loads(row["parsed"])
        c["parsed_sectors"] = list(c.get("sectors", []))
        overrides = json.loads(row["overrides"])
        c.update({k: v for k, v in overrides.items() if v not in (None, "", [])})
        c["overrides"] = overrides
        c.update(id=row["id"], filename=row["filename"], stored_name=row["stored_name"],
                 uploaded_at=row["uploaded_at"], notes=row["notes"], error=row["error"])
        if with_text:
            c["text"] = row["text"]
        return c

    def get(self, cid):
        row = self.conn.execute("SELECT * FROM candidates WHERE id=?", (cid,)).fetchone()
        return self._candidate(row, with_text=True) if row else None

    def all(self):
        rows = self.conn.execute(
            "SELECT id, filename, stored_name, uploaded_at, parsed, overrides, notes, error "
            "FROM candidates ORDER BY id DESC").fetchall()
        return [self._candidate(r) for r in rows]

    def stats(self):
        row = self.conn.execute(
            "SELECT COUNT(*) n, SUM(error != '') errors FROM candidates").fetchone()
        return {"total": row["n"] or 0, "errors": row["errors"] or 0}

    def keyword_hits(self, keywords):
        """Return {candidate_id: (relevance, snippet_html)} for CVs containing every keyword."""
        if not keywords:
            return None
        match = " AND ".join('"' + k.replace('"', "") + '"' for k in keywords)
        try:
            rows = self.conn.execute(
                "SELECT rowid, bm25(cv_fts) AS rank, "
                "snippet(cv_fts, 0, char(2), char(3), ' … ', 20) AS snip "
                "FROM cv_fts WHERE cv_fts MATCH ?", (match,)).fetchall()
        except sqlite3.OperationalError:
            return {}
        return {r["rowid"]: (-r["rank"], _mark(r["snip"])) for r in rows}

    def context_snippet(self, cid, synonyms, width=110):
        row = self.conn.execute("SELECT text FROM candidates WHERE id=?", (cid,)).fetchone()
        if not row or not synonyms:
            return ""
        text = re.sub(r"\s+", " ", row["text"])
        m = pattern_for(synonyms).search(text)
        if not m:
            return ""
        start, end = max(m.start() - width, 0), min(m.end() + width, len(text))
        snip = ("… " if start else "") + text[start:m.start()] + "\x02" + m.group(0) + "\x03" + \
            text[m.end():end] + (" …" if end < len(text) else "")
        return _mark(snip)


def _mark(s):
    from markupsafe import escape

    return str(escape(s)).replace("\x02", "<mark>").replace("\x03", "</mark>")


def sector_synonyms(sectors):
    return [s for sector in sectors for s in taxonomy.SECTORS.get(sector, [])]
