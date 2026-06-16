from typing import List
from config import TOP_K_RETRIEVAL, SIMILARITY_THRESHOLD
from services.vectorstore.document import Document
from services.vectorstore.faiss_store import get_contract_collection, get_legal_collection


def retrieve_contract(query: str, contract_id: str, k: int = None) -> List[Document]:
    return get_contract_collection().similarity_search(
        query, k=k or TOP_K_RETRIEVAL, where={"contract_id": contract_id}, min_score=SIMILARITY_THRESHOLD
    )


def retrieve_legal(query: str, k: int = 3) -> List[Document]:
    return get_legal_collection().similarity_search(query, k=k, min_score=SIMILARITY_THRESHOLD)
