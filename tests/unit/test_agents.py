from models import ContractAnalysis, RiskItem


def test_contract_analysis_schema():
    data = {
        "contract_id": "test-id",
        "contract_type": "Hợp đồng lao động",
        "parties": [{"name": "Công ty A", "role": "Bên A"}],
        "clauses": [{"clause_number": "1", "title": "Điều khoản chung", "summary": "Nội dung"}],
    }
    analysis = ContractAnalysis(**data)
    assert analysis.contract_id == "test-id"
    assert len(analysis.parties) == 1
    assert analysis.parties[0].name == "Công ty A"


def test_risk_item_schema():
    item = RiskItem(clause_ref="Điều 5", issue="Thiếu điều khoản phạt", severity="warning")
    assert item.severity == "warning"
    assert item.clause_ref == "Điều 5"
