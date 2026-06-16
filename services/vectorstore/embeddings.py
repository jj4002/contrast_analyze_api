import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, EMBEDDING_DEVICE, logger

_model = None


def _resolve_device() -> str:
    if EMBEDDING_DEVICE != "auto":
        return EMBEDDING_DEVICE
    return "cuda" if torch.cuda.is_available() else "cpu"


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        device = _resolve_device()
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL} on device={device}")
        _model = SentenceTransformer(EMBEDDING_MODEL, device=device, trust_remote_code=True)
    return _model


def get_embedding_dim() -> int:
    return get_embedding_model().get_sentence_embedding_dimension()


def embed_texts(texts: list[str]) -> np.ndarray:
    vectors = get_embedding_model().encode(texts, normalize_embeddings=True)
    return np.asarray(vectors, dtype="float32")
