from fastapi import UploadFile
from config import logger
from database import get_db
from models import UploadResponse, AnalyzeResponse, ChatResponse
from services.document.file_handler import save_upload
from services.document.parser import parse_document
from services.document.chunker import chunk_by_clause
from services.vectorstore.faiss_store import get_contract_collection
from services.agents.workflow import run_analysis_workflow
from services.agents.qa_agent import answer_question
from services.agents._llm import DEFAULT_PROVIDER


def _assert_owns_contract(contract_id: str, user_id: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM uploaded_contracts WHERE contract_id = %s AND user_id = %s", (contract_id, user_id))
            if cur.fetchone() is None:
                raise ValueError(f"No documents found for contract: {contract_id}")


async def upload_contract(file: UploadFile, user_id: str) -> UploadResponse:
    contract_id, file_path, file_ext = await save_upload(file)
    filename = file.filename or "unknown"
    status, message, chunk_count = "uploaded", f"File uploaded successfully: {filename}", 0

    try:
        text = parse_document(file_path, file_ext)
        docs = chunk_by_clause(text, contract_id)
        get_contract_collection().add_documents(docs)
        chunk_count = len(docs)
        status, message = "parsed", f"{filename} parsed and indexed with {chunk_count} chunks"
    except Exception as e:
        logger.error(f"Parse error: {e}")
        message = f"File uploaded but parsing failed: {str(e)}"

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO uploaded_contracts (contract_id, user_id, filename, file_type, file_path, status, message, chunk_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (contract_id) DO UPDATE SET status = EXCLUDED.status, message = EXCLUDED.message, chunk_count = EXCLUDED.chunk_count",
                (contract_id, user_id, filename, file_ext, file_path, status, message, chunk_count),
            )

    return UploadResponse(contract_id=contract_id, filename=filename, file_type=file_ext, status=status, message=message, chunk_count=chunk_count)


async def analyze_contract(contract_id: str, user_id: str, provider: str = DEFAULT_PROVIDER) -> AnalyzeResponse:
    _assert_owns_contract(contract_id, user_id)

    all_docs = get_contract_collection().get(where={"contract_id": contract_id})
    if not all_docs or not all_docs.get("documents"):
        raise ValueError(f"No documents found for contract: {contract_id}")
    full_text = "\n".join(all_docs["documents"])
    analysis, risks = await run_analysis_workflow(full_text, contract_id, provider)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE uploaded_contracts SET status = %s WHERE contract_id = %s", ("analyzed", contract_id))

    return AnalyzeResponse(contract_id=contract_id, analysis=analysis.model_dump(), risks=[r.model_dump() for r in risks])


async def chat_with_contract(contract_id: str, question: str, history: list, user_id: str, provider: str = DEFAULT_PROVIDER) -> ChatResponse:
    _assert_owns_contract(contract_id, user_id)
    return answer_question(question, contract_id, history, provider)
