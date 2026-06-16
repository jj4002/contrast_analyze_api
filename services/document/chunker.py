import re
import unicodedata
from typing import List
from services.vectorstore.document import Document
from config import MAX_CHUNK_SIZE, CHUNK_OVERLAP

_SEPARATORS = ["\n\n", "\n", ".", " ", ""]


def _split_text(text: str, chunk_size: int, chunk_overlap: int, separators: List[str] = None) -> List[str]:
    """Recursively split text on the first separator that fits, applying overlap between chunks."""
    if len(text) <= chunk_size:
        return [text] if text else []

    separators = _SEPARATORS if separators is None else separators
    sep = separators[0]
    rest = separators[1:]
    parts = text.split(sep) if sep else list(text)

    chunks, current = [], ""
    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(part) > chunk_size and rest:
                chunks.extend(_split_text(part, chunk_size, chunk_overlap, rest))
                current = ""
            else:
                current = part
    if current:
        chunks.append(current)

    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            overlapped.append(chunks[i - 1][-chunk_overlap:] + chunks[i])
        return overlapped
    return chunks


def chunk_by_clause(text: str, contract_id: str) -> List[Document]:
    text = unicodedata.normalize("NFC", text)
    clause_pattern = r"(?:(?:Điều|ĐIỀU|Khoản|KHOẢN)\s+\d+[\.:\-\)]\s*)"

    splits = re.split(f"({clause_pattern})", text)
    documents = []
    chunk_index = 0

    if splits and splits[0].strip():
        preamble = splits[0].strip()
        if len(preamble) > MAX_CHUNK_SIZE:
            for chunk in _split_text(preamble, MAX_CHUNK_SIZE, CHUNK_OVERLAP):
                chunk_index += 1
                documents.append(Document(
                    page_content=chunk,
                    metadata={"contract_id": contract_id, "clause_number": "Preamble", "chunk_index": chunk_index},
                ))
        else:
            chunk_index += 1
            documents.append(Document(
                page_content=preamble,
                metadata={"contract_id": contract_id, "clause_number": "Preamble", "chunk_index": chunk_index},
            ))

    for i in range(1, len(splits), 2):
        header = splits[i]
        content = splits[i + 1] if i + 1 < len(splits) else ""
        chunk_text = (header + content).strip()
        if not chunk_text:
            continue

        num = re.search(r"(\d+)", header)
        clause_number = num.group(1) if num else str(chunk_index)

        if len(chunk_text) > MAX_CHUNK_SIZE:
            for chunk in _split_text(chunk_text, MAX_CHUNK_SIZE, CHUNK_OVERLAP):
                chunk_index += 1
                documents.append(Document(
                    page_content=chunk,
                    metadata={"contract_id": contract_id, "clause_number": clause_number, "chunk_index": chunk_index},
                ))
        else:
            chunk_index += 1
            documents.append(Document(
                page_content=chunk_text,
                metadata={"contract_id": contract_id, "clause_number": clause_number, "chunk_index": chunk_index},
            ))

    has_only_preamble = (
        len(documents) == 1 and documents[0].metadata["clause_number"] == "Preamble"
    ) if documents else True

    if not documents or has_only_preamble:
        documents = []
        for idx, chunk in enumerate(_split_text(text, MAX_CHUNK_SIZE, CHUNK_OVERLAP)):
            if chunk.strip():
                documents.append(Document(
                    page_content=chunk.strip(),
                    metadata={"contract_id": contract_id, "clause_number": str(idx + 1), "chunk_index": idx + 1},
                ))

    return documents
