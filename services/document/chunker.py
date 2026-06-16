import re
import unicodedata
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import MAX_CHUNK_SIZE, CHUNK_OVERLAP


def chunk_by_clause(text: str, contract_id: str) -> List[Document]:
    text = unicodedata.normalize("NFC", text)
    clause_pattern = r"(?:(?:Điều|ĐIỀU|Khoản|KHOẢN)\s+\d+[\.:\-\)]\s*)"

    splits = re.split(f"({clause_pattern})", text)
    documents = []
    chunk_index = 0

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    if splits and splits[0].strip():
        preamble = splits[0].strip()
        if len(preamble) > MAX_CHUNK_SIZE:
            for chunk in splitter.split_text(preamble):
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
            for chunk in splitter.split_text(chunk_text):
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
        for idx, chunk in enumerate(splitter.split_text(text)):
            if chunk.strip():
                documents.append(Document(
                    page_content=chunk.strip(),
                    metadata={"contract_id": contract_id, "clause_number": str(idx + 1), "chunk_index": idx + 1},
                ))

    return documents
