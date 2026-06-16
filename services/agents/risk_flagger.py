from typing import List
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from models import RiskItem
from prompts import RISK_FLAG_PROMPT
from services.agents._llm import get_llm
from services.vectorstore.retriever import retrieve_legal


def flag_risks(contract_text: str, contract_id: str) -> List[RiskItem]:
    legal_docs = retrieve_legal("vi phạm hợp đồng rủi ro pháp lý", k=3)
    legal_context = "\n\n".join([d.page_content for d in legal_docs]) if legal_docs else "Không có dữ liệu pháp luật liên quan."
    chain = (PromptTemplate(template=RISK_FLAG_PROMPT, input_variables=["contract_text", "legal_context"])
             | get_llm() | JsonOutputParser())
    result = chain.invoke({"contract_text": contract_text[:10000], "legal_context": legal_context})
    if isinstance(result, list):
        return [RiskItem(
            clause_ref=item.get("clause_ref", ""),
            issue=item.get("issue", ""),
            severity=item.get("severity", "ok"),
            legal_basis=item.get("legal_basis"),
            recommendation=item.get("recommendation"),
        ) for item in result]
    return []
