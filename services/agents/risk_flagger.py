import json
import re
from typing import List
from models import RiskItem
from prompts import RISK_FLAG_PROMPT
from config import logger
from services.agents._llm import chat_completion, DEFAULT_PROVIDER
from services.agents.topic_retriever import (
    detect_topics, retrieve_law_for_topics, format_legal_context_with_status,
)


def _parse_json_array(raw: str):
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)


def flag_risks(contract_text: str, contract_id: str, provider: str = DEFAULT_PROVIDER) -> List[RiskItem]:
    # Topic-aware legal retrieval instead of hardcoded query
    topics = detect_topics(contract_text)
    logger.info(f"[RiskFlag] Detected topics: {topics}")

    legal_by_topic = retrieve_law_for_topics(topics, k=3)

    # Merge all legal docs across topics
    all_legal_docs = []
    seen_texts = set()
    for docs in legal_by_topic.values():
        for d in docs:
            h = hash(d.page_content[:200])
            if h not in seen_texts:
                seen_texts.add(h)
                all_legal_docs.append(d)

    logger.info(f"[RiskFlag] Total legal chunks retrieved: {len(all_legal_docs)}")
    legal_context = format_legal_context_with_status(all_legal_docs)

    prompt = RISK_FLAG_PROMPT.format(
        contract_text=contract_text[:10000],
        legal_context=legal_context,
    )
    raw = chat_completion(prompt, provider=provider)

    try:
        result = _parse_json_array(raw)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse risk flagger output for {contract_id}: {e}")
        return []

    if isinstance(result, list):
        return [RiskItem(
            clause_ref=item.get("clause_ref", ""),
            issue=item.get("issue", ""),
            severity=item.get("severity", "ok"),
            legal_basis=item.get("legal_basis"),
            recommendation=item.get("recommendation"),
        ) for item in result]
    return []
