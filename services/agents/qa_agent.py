from models import ChatResponse
from prompts import QA_PROMPT
from services.agents._llm import chat_completion, DEFAULT_PROVIDER
from services.vectorstore.retriever import retrieve_contract, retrieve_legal


def answer_question(question: str, contract_id: str, chat_history: list, provider: str = DEFAULT_PROVIDER) -> ChatResponse:
    contract_docs = retrieve_contract(question, contract_id)
    contract_context = "\n\n".join([d.page_content for d in contract_docs]) if contract_docs else "Không có dữ liệu hợp đồng."
    legal_docs = retrieve_legal(question, k=3)
    legal_context = "\n\n".join([d.page_content for d in legal_docs]) if legal_docs else "Không có dữ liệu pháp luật liên quan."
    history_str = "\n".join(
        [f"User: {m.get('question', '')}\nAssistant: {m.get('answer', '')}" for m in chat_history[-5:]]
    ) if chat_history else "Không có lịch sử."

    prompt = QA_PROMPT.format(
        contract_context=contract_context[:8000],
        legal_context=legal_context[:3000],
        chat_history=history_str,
        question=question,
    )
    answer = chat_completion(prompt, provider=provider)

    source_clauses = list(set(
        d.metadata.get("clause_number", "") for d in contract_docs if d.metadata.get("clause_number")
    ))
    return ChatResponse(answer=answer, source_clauses=source_clauses, contract_id=contract_id)
