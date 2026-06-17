import json
import re
import asyncio
from typing import Tuple, List
from models import ContractAnalysis, RiskItem
from config import logger
from prompts import (
    ANALYZE_CLAUSE_PROMPT,
    EVALUATE_CLAUSE_PROMPT,
    RECOMMEND_PROMPT,
)
from services.agents.clause_parser import parse_contract
from services.agents._llm import chat_completion, DEFAULT_PROVIDER
from services.agents.topic_retriever import (
    detect_topics_from_clauses,
    retrieve_law_for_topic,
    format_legal_context_with_status,
    format_clause_with_topic,
)


def _parse_json(raw: str) -> dict:
    """Robust JSON parser from LLM output."""
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    # Try to find first { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def _extract_contract_info(analysis: ContractAnalysis) -> str:
    """Format contract metadata for prompt."""
    parts = []
    if analysis.contract_type:
        parts.append(f"Loại: {analysis.contract_type}")
    if analysis.parties:
        parts.append("Các bên:")
        for p in analysis.parties:
            parts.append(f"  - {p.role}: {p.name}")
    if analysis.start_date:
        parts.append(f"Ngày bắt đầu: {analysis.start_date}")
    if analysis.end_date:
        parts.append(f"Ngày kết thúc: {analysis.end_date}")
    if analysis.contract_value:
        parts.append(f"Giá trị: {analysis.contract_value}")
    return "\n".join(parts) if parts else "Không có thông tin hợp đồng."


def _extract_clause_dicts(text: str) -> List[dict]:
    """Extract individual clause sections from full contract text.

    Returns list of {clause_number, text} dicts.
    """
    clause_pattern = re.compile(
        r"(?:^|\n)\s*(Điều|ĐIỀU)\s+(\d+)\s*[\.:\)\-]\s*",
        re.MULTILINE,
    )
    matches = list(clause_pattern.finditer(text))

    if not matches:
        return [{"clause_number": "0", "text": text}]

    clauses = []
    for i, m in enumerate(matches):
        header = m.group(0)
        num = m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        clauses.append({
            "clause_number": num,
            "text": header + text[start:end].strip(),
        })

    # Add preamble if exists before first match
    if matches[0].start() > 0:
        preamble = text[:matches[0].start()].strip()
        if preamble:
            clauses.insert(0, {"clause_number": "0", "text": preamble})

    return clauses


async def run_analysis_workflow(
    contract_text: str, contract_id: str, provider: str = DEFAULT_PROVIDER
) -> Tuple[ContractAnalysis, List[RiskItem]]:
    """3-step pipeline: Rule-based parse → LLM analyze/evaluate → LLM recommend.

    Returns (analysis, risks) — risks now includes detailed evaluation.
    """
    logger.info(f"Starting analysis workflow for contract: {contract_id} (provider={provider})")

    # ── Step 1: Rule-based parsing (existing, unchanged) ──
    try:
        analysis = await asyncio.to_thread(parse_contract, contract_text, contract_id)
    except Exception as e:
        logger.error(f"Rule-based parsing failed: {e}, falling back")
        analysis = ContractAnalysis(contract_id=contract_id)

    # ── Step 2: Extract clauses & run analyze + evaluate per clause ──
    clauses = _extract_clause_dicts(contract_text)
    logger.info(f"[Workflow] Found {len(clauses)} clauses to analyze")

    all_risks: List[RiskItem] = []
    all_evaluations = []
    contract_info = _extract_contract_info(analysis)

    for clause in clauses:
        clause_num = clause["clause_number"]
        clause_text = clause["text"][:5000]

        # Detect topic for this clause
        topic_info = detect_topics_from_clauses(clause_text)
        topic = list(topic_info.keys())[0] if topic_info else "general"

        # Retrieve relevant law for this clause's topic
        legal_docs = retrieve_law_for_topic(topic, k=3) if topic != "general" else []
        legal_context = format_legal_context_with_status(legal_docs)

        try:
            # ── 2a: Analyze clause ──
            analyze_prompt = ANALYZE_CLAUSE_PROMPT.format(
                contract_clause=clause_text,
                legal_context=legal_context[:4000],
            )
            raw_analysis = await asyncio.to_thread(
                chat_completion, analyze_prompt, provider
            )
            analyzed = _parse_json(raw_analysis)
            logger.info(f"[Workflow] Analyzed clause {clause_num}: topic={topic}")

            # ── 2b: Evaluate clause ──
            evaluate_prompt = EVALUATE_CLAUSE_PROMPT.format(
                analyzed_clause=json.dumps(analyzed, ensure_ascii=False),
                legal_context=legal_context[:4000],
            )
            raw_eval = await asyncio.to_thread(
                chat_completion, evaluate_prompt, provider
            )
            evaluated = _parse_json(raw_eval)

            severity = evaluated.get("severity", "ok")
            logger.info(f"[Workflow] Evaluated clause {clause_num}: severity={severity}")

            all_evaluations.append(evaluated)

            if severity in ("critical", "warning"):
                all_risks.append(RiskItem(
                    clause_ref=evaluated.get("clause_ref", f"Điều {clause_num}"),
                    issue=evaluated.get("issue", ""),
                    severity=severity,
                    legal_basis=evaluated.get("legal_basis"),
                    recommendation=evaluated.get("recommendation"),
                ))

        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"[Workflow] JSON parse failed for clause {clause_num}: {e}")
            continue
        except Exception as e:
            logger.error(f"[Workflow] Failed processing clause {clause_num}: {e}")
            continue

    # ── Step 3: Generate overall recommendation ──
    if all_evaluations:
        try:
            recommend_prompt = RECOMMEND_PROMPT.format(
                contract_info=contract_info,
                all_evaluations=json.dumps(all_evaluations, ensure_ascii=False, indent=2),
            )
            raw_recommend = await asyncio.to_thread(
                chat_completion, recommend_prompt, provider
            )
            recommend = _parse_json(raw_recommend)
            logger.info(f"[Workflow] Overall risk: {recommend.get('overall_risk', 'unknown')}")

            # Add top_actions as risk items for the frontend
            for action in recommend.get("top_actions", [])[:5]:
                all_risks.append(RiskItem(
                    clause_ref="",
                    issue=action,
                    severity="info",
                    legal_basis=None,
                    recommendation=action,
                ))

        except Exception as e:
            logger.error(f"[Workflow] Recommendation step failed: {e}")

    logger.info(f"Analysis workflow completed for {contract_id}: {len(all_risks)} risks found")
    return analysis, all_risks
