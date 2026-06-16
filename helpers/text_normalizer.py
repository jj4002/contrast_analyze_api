import unicodedata
import re


def normalize_query_text(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize('NFD', text)
    text = text.replace('đ', 'd')
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def normalize_for_cache_key(text: str, intent: str = "", entity: str = "") -> str:
    key = normalize_query_text(text)
    if intent:
        key = f"{key}:{intent}"
    if entity:
        key = f"{key}:{entity}"
    return key


def normalize_doc_number(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = re.sub(r'[^a-z0-9]', '', text)
    return text
