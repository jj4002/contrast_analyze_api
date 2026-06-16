import os
from langchain_chroma import Chroma
from config import CHROMA_PERSIST_DIR
from services.vectorstore.embeddings import get_embeddings


def get_contract_collection() -> Chroma:
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    return Chroma(collection_name="contracts", embedding_function=get_embeddings(), persist_directory=CHROMA_PERSIST_DIR)


def get_legal_collection() -> Chroma:
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    return Chroma(collection_name="legal_kb", embedding_function=get_embeddings(), persist_directory=CHROMA_PERSIST_DIR)
