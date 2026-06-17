"""
TVPL Database Service — Supabase PostgreSQL.
Quản lý kết nối, schema, CRUD cho bảng legal_documents.
"""
from __future__ import annotations

import logging
from typing import Optional, Set, Dict, List

import psycopg2
import psycopg2.extras

from config import DATABASE_URL, SUPABASE_URL

logger = logging.getLogger(__name__)

_conn: Optional[psycopg2.extensions.connection] = None

# Schema SQL — CREATE IF NOT EXISTS, giống supabase_export/schema.sql
ENSURE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS legal_documents (
    doc_id          TEXT PRIMARY KEY,
    doc_number      TEXT NOT NULL,
    title           TEXT NOT NULL,
    doc_type        TEXT,
    issued_date     TEXT,
    effective_date  TEXT,
    content         TEXT NOT NULL,
    url             TEXT,
    category        TEXT,
    year_published  INTEGER,
    signer          TEXT,
    issuing_authority TEXT,
    status_flag     INTEGER DEFAULT 0,
    expiry_date     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ld_doc_number  ON legal_documents(doc_number);
CREATE INDEX IF NOT EXISTS idx_ld_year        ON legal_documents(year_published);
CREATE INDEX IF NOT EXISTS idx_ld_category    ON legal_documents(category);
CREATE INDEX IF NOT EXISTS idx_ld_url         ON legal_documents(url);
CREATE INDEX IF NOT EXISTS idx_ld_status      ON legal_documents(status_flag);
CREATE INDEX IF NOT EXISTS idx_ld_eff_date    ON legal_documents(effective_date);
CREATE INDEX IF NOT EXISTS idx_ld_dedup       ON legal_documents(doc_number, issued_date, signer);
"""


def get_conn() -> psycopg2.extensions.connection:
    global _conn
    if _conn is None or _conn.closed:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set in .env")
        _conn = psycopg2.connect(DATABASE_URL, connect_timeout=30)
        _conn.autocommit = False
        with _conn.cursor() as cur:
            cur.execute(ENSURE_SCHEMA_SQL)
            _conn.commit()
        logger.info(f"Connected to Supabase: {SUPABASE_URL}")
    return _conn


def close():
    global _conn
    if _conn and not _conn.closed:
        _conn.close()
        _conn = None


def get_all_urls() -> Set[str]:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT url FROM legal_documents WHERE url IS NOT NULL")
        return {r[0] for r in cur.fetchall()}


def check_duplicate(doc_number: str, issued_date: str, signer: str) -> Optional[Dict]:
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT doc_id, status_flag, title, url FROM legal_documents "
            "WHERE doc_number = %s AND issued_date = %s AND signer = %s",
            (doc_number, issued_date or "", signer or ""),
        )
        return dict(cur.fetchone()) if cur.rowcount > 0 else None


def insert_document(
    doc_id: str,
    title: str,
    content: str,
    doc_number: Optional[str] = None,
    doc_type: Optional[str] = None,
    issued_date: Optional[str] = None,
    effective_date: Optional[str] = None,
    url: Optional[str] = None,
    category: Optional[str] = None,
    year_published: Optional[int] = None,
    signer: Optional[str] = None,
    issuing_authority: Optional[str] = None,
    expiry_date: Optional[str] = None,
) -> bool:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO legal_documents
                    (doc_id, doc_number, title, doc_type, issued_date, effective_date,
                     expiry_date, content, url, category, year_published,
                     signer, issuing_authority)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    doc_number = EXCLUDED.doc_number,
                    title = EXCLUDED.title,
                    doc_type = EXCLUDED.doc_type,
                    issued_date = EXCLUDED.issued_date,
                    effective_date = EXCLUDED.effective_date,
                    expiry_date = EXCLUDED.expiry_date,
                    content = EXCLUDED.content,
                    url = EXCLUDED.url,
                    category = EXCLUDED.category,
                    year_published = EXCLUDED.year_published,
                    signer = EXCLUDED.signer,
                    issuing_authority = EXCLUDED.issuing_authority,
                    updated_at = NOW()
            """, (
                doc_id, doc_number or doc_id, title, doc_type,
                issued_date, effective_date, expiry_date,
                content, url, category,
                year_published, signer, issuing_authority,
            ))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Insert failed for {doc_id}: {e}")
        conn.rollback()
        return False


def get_total_docs() -> int:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM legal_documents")
        return cur.fetchone()[0]


def get_document_by_id(doc_id: str) -> Optional[Dict]:
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM legal_documents WHERE doc_id = %s", (doc_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_document_by_number(doc_number: str) -> Optional[Dict]:
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM legal_documents WHERE doc_number = %s", (doc_number,))
        row = cur.fetchone()
        return dict(row) if row else None
