import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Generator
from config import DATABASE_URL, logger


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn


@contextmanager
def get_db() -> Generator:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS uploaded_contracts (
                    id BIGSERIAL PRIMARY KEY,
                    contract_id TEXT NOT NULL UNIQUE,
                    user_id UUID NOT NULL,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    message TEXT,
                    chunk_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("ALTER TABLE uploaded_contracts ADD COLUMN IF NOT EXISTS user_id UUID")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id BIGSERIAL PRIMARY KEY,
                    contract_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    source_clauses TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_contracts_id ON uploaded_contracts(contract_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_contracts_user ON uploaded_contracts(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_contract ON chat_history(contract_id)")
    logger.info("PostgreSQL database initialized")
