import os
import hashlib
from config import LEGAL_DOCS_DIR, logger
from services.document.parser import parse_pdf
from services.document.chunker import chunk_by_clause
from services.vectorstore.chroma_client import get_legal_collection


_processed_hashes = set()


def get_file_hash(file_path: str) -> str:
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while buf := f.read(65536):
            hasher.update(buf)
    return hasher.hexdigest()


def load_legal_documents() -> int:
    if not os.path.exists(LEGAL_DOCS_DIR):
        logger.warning(f"Legal docs directory not found: {LEGAL_DOCS_DIR}")
        return 0
    total_chunks = 0
    db = get_legal_collection()
    for filename in os.listdir(LEGAL_DOCS_DIR):
        if not filename.lower().endswith(".pdf"):
            continue
        file_path = os.path.join(LEGAL_DOCS_DIR, filename)
        fh = get_file_hash(file_path)
        if fh in _processed_hashes:
            continue
        try:
            logger.info(f"Loading legal document: {filename}")
            text = parse_pdf(file_path)
            docs = chunk_by_clause(text, filename)
            for d in docs:
                d.metadata["source"] = filename
            db.add_documents(docs)
            _processed_hashes.add(fh)
            total_chunks += len(docs)
            logger.info(f"Added {len(docs)} chunks from {filename}")
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")
    return total_chunks
