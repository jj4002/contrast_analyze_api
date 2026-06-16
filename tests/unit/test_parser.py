import pytest
from services import parse_pdf, parse_document


def test_parse_pdf_invalid_path():
    with pytest.raises(ValueError):
        parse_pdf("nonexistent.pdf")


def test_parse_pdf_empty_file(tmp_path):
    p = tmp_path / "empty.pdf"
    p.write_text("not a pdf")
    with pytest.raises(ValueError):
        parse_pdf(str(p))


def test_parse_document_unsupported():
    with pytest.raises(ValueError, match="Unsupported"):
        parse_document("test.xyz", ".xyz")
