from services import chunk_by_clause


def test_chunk_by_clause_with_pattern():
    text = "Điều 1. Nội dung hợp đồng\nĐây là nội dung.\nĐiều 2. Nghĩa vụ\nNghĩa vụ các bên."
    docs = chunk_by_clause(text, "test-1")
    assert len(docs) >= 2
    assert all(d.metadata["contract_id"] == "test-1" for d in docs)


def test_chunk_by_clause_fallback():
    text = "A" * 2000
    docs = chunk_by_clause(text, "test-2")
    assert len(docs) >= 1
    assert docs[0].metadata["contract_id"] == "test-2"
