from typing import List
from langchain_core.documents import Document
from config import TOP_K_RETRIEVAL
from services.vectorstore.chroma_client import get_contract_collection, get_legal_collection


def retrieve_contract(query: str, contract_id: str, k: int = None) -> List[Document]:
    return get_contract_collection().as_retriever(
        search_kwargs={"k": k or TOP_K_RETRIEVAL, "filter": {"contract_id": contract_id}}
    ).invoke(query)


def retrieve_legal(query: str, k: int = None) -> List[Document]:
    return get_legal_collection().as_retriever(
        search_kwargs={"k": k or TOP_K_RETRIEVAL}
    ).invoke(query)
