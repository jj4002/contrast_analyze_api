from config import logger, LEGAL_KB_BATCH_SIZE, LEGAL_KB_ACTIVE_ONLY, EMBED_MAX_CHARS
from database import get_db
from services.vectorstore.document import Document
from services.vectorstore.faiss_store import get_legal_collection

_QUERY = """
    SELECT dc.chunk_ref, dc.doc_id, dc.chunk_index, dc.chunk_text, dc.section_type,
           ld.title, ld.doc_number, ld.category,
           ld.status_flag, ld.effective_date, ld.expiry_date
    FROM document_chunks dc
    JOIN legal_documents ld ON ld.doc_id = dc.doc_id
    {where_clause}
    ORDER BY dc.doc_id, dc.chunk_index
"""


def load_legal_documents() -> int:
    """Rebuild the legal FAISS collection from Supabase.

    Includes status_flag, effective_date, expiry_date for expiration/amendment handling.
    """
    where_clause = "WHERE ld.status_flag = 1" if LEGAL_KB_ACTIVE_ONLY else ""
    collection = get_legal_collection()
    collection.reset()

    total_chunks = 0
    batch: list[Document] = []

    with get_db() as conn:
        with conn.cursor(name="legal_kb_cursor") as cur:
            cur.itersize = LEGAL_KB_BATCH_SIZE
            cur.execute(_QUERY.format(where_clause=where_clause))

            for row in cur:
                (chunk_ref, doc_id, chunk_index, chunk_text, section_type,
                 title, doc_number, category,
                 status_flag, effective_date, expiry_date) = row

                if not chunk_text or not chunk_text.strip():
                    continue
                # Truncate to model's max token limit before embedding
                page_text = chunk_text[:EMBED_MAX_CHARS]
                batch.append(Document(
                    page_content=page_text,
                    metadata={
                        "chunk_ref": chunk_ref,
                        "doc_id": doc_id,
                        "chunk_index": chunk_index,
                        "section_type": section_type,
                        "title": title,
                        "doc_number": doc_number,
                        "category": category,
                        "status_flag": status_flag,
                        "effective_date": effective_date or "",
                        "expiry_date": expiry_date or "",
                    },
                ))

                if len(batch) >= LEGAL_KB_BATCH_SIZE:
                    collection.add_documents(batch, persist=False)
                    total_chunks += len(batch)
                    logger.info(f"Loaded {total_chunks} legal chunks so far...")
                    batch = []

    if batch:
        collection.add_documents(batch, persist=False)
        total_chunks += len(batch)

    collection.save()
    logger.info(f"Legal KB loaded from Supabase: {total_chunks} chunks indexed")
    return total_chunks
