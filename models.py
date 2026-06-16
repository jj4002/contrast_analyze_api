from pydantic import BaseModel, Field
from typing import Optional, List, Any


class Party(BaseModel):
    name: str
    role: str
    address: Optional[str] = None
    tax_id: Optional[str] = None
    representative: Optional[str] = None


class Clause(BaseModel):
    clause_number: str
    title: Optional[str] = None
    summary: str


class RiskItem(BaseModel):
    clause_ref: str
    issue: str
    severity: str = Field(..., pattern="^(critical|warning|ok)$")
    legal_basis: Optional[str] = None
    recommendation: Optional[str] = None


class ContractAnalysis(BaseModel):
    contract_id: str
    contract_type: Optional[str] = None
    parties: List[Party] = []
    execution_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None
    contract_value: Optional[str] = None
    payment_terms: Optional[str] = None
    payment_method: Optional[str] = None
    termination_clause: Optional[str] = None
    penalty_clause: Optional[str] = None
    indemnity: Optional[str] = None
    force_majeure: Optional[str] = None
    governing_law: Optional[str] = None
    dispute_resolution: Optional[str] = None
    confidentiality: Optional[str] = None
    severability: Optional[str] = None
    amendments: Optional[str] = None
    clauses: List[Clause] = []


class UploadResponse(BaseModel):
    contract_id: str
    filename: str
    file_type: str
    status: str
    message: str
    chunk_count: int = 0


class AnalyzeResponse(BaseModel):
    contract_id: str
    analysis: Any
    risks: List[Any]


class ChatResponse(BaseModel):
    answer: str
    source_clauses: List[str]
    contract_id: str
