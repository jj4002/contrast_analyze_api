from langchain_huggingface import HuggingFaceEmbeddings
from config import EMBEDDING_MODEL, logger


_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        try:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            _embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception as e:
            logger.warning(f"Fallback embedding: {e}")
            _embeddings = HuggingFaceEmbeddings(
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
    return _embeddings
