import re
import unicodedata
from typing import List, Optional
from models import ContractAnalysis, Party, Clause
from config import logger


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_line_around(text: str, keyword: str, context_lines: int = 2) -> Optional[str]:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.search(keyword, line, re.IGNORECASE):
            start = max(0, i)
            end = min(len(lines), i + context_lines + 1)
            result = "\n".join(lines[start:end])
            result = re.sub(r"\n(?:Điều|ĐIỀU)\s+\d+.*$", "", result)
            return _normalize(result).strip()
    return None


def _find_first_match(text: str, patterns: List[str]) -> Optional[str]:
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            val = m.group(1).strip()
            if val and len(val) > 1:
                return val
    return None


# ============================================================
#  Nhóm 1: Các bên tham gia
# ============================================================

_PARTY_A_RE = re.compile(
    r"(?:BÊN\s+A|Bên\s+A)\s*:?\s*\(?\s*(?P<role>[^)\n]*?)\s*\)?\s*\n",
    re.IGNORECASE,
)
_PARTY_B_RE = re.compile(
    r"(?:BÊN\s+B|Bên\s+B)\s*:?\s*\(?\s*(?P<role>[^)\n]*?)\s*\)?\s*\n",
    re.IGNORECASE,
)

_COMPANY_NAME_RE = re.compile(
    r"(?:Công\s+ty|CÔNG\s+TY|Doanh\s+nghiệp)\s*[:\t]+\s*(.+)",
    re.IGNORECASE,
)

_EMPLOYEE_TABLE_RE = re.compile(
    r"(?:Họ\s+và\s+tên|HỌ\s+TÊN|Họ\s+tên)\s*\|?\s*[:\t]+\s*(.+?)(?:\t|\||\n|Giới\s+tính|Sinh\s+ngày)",
    re.IGNORECASE,
)

_CMND_RE = re.compile(
    r"(?:CMND|CCCD)\s*(?:số\s*)?\s*[:\|\t\-\s]+\s*(\d{9,12})",
    re.IGNORECASE,
)

_ADDRESS_RE = re.compile(
    r"(?:Địa\s+chỉ|Đia\s+chỉ)\s*[:\|\t]+\s*(.+?)(?:\t|\||\n|Điện\s+thoại|$)",
    re.IGNORECASE,
)


def _extract_parties(text: str) -> List[Party]:
    parties = []

    party_a_match = _PARTY_A_RE.search(text)
    party_b_match = _PARTY_B_RE.search(text)

    _extract_party_a(text, party_a_match, parties)
    _extract_party_b(text, party_b_match, parties)

    return parties


def _extract_party_a(text: str, match, parties: List[Party]):
    if not match:
        return

    role = (match.group("role") or "Người sử dụng lao động").strip()
    start = match.end()
    end = start + 2000
    block = text[start:end]

    name = None
    address = None
    tax_id = None
    representative = None

    m = _COMPANY_NAME_RE.search(block)
    if m:
        name = m.group(1).strip()

    m = re.search(r"Mã\s+số\s+thuế\s*[:\t]+\s*(\d+)", block, re.IGNORECASE)
    if m:
        tax_id = m.group(1).strip()

    m = _ADDRESS_RE.search(block)
    if not m:
        m = re.search(r"(?:Địa\s+chỉ|Đia\s+chỉ)\s*[:\|\t]+\s*(.+?)(?:\t|\||\n|Điện\s+thoại|$)", block, re.IGNORECASE)
    if m:
        address = m.group(1).strip()

    m = re.search(r"(?:Đại\s+diện|ĐẠI\s+DIỆN)\s*[:\t]+\s*(.+)", block, re.IGNORECASE)
    if m:
        representative = m.group(1).strip()[:120]

    if name:
        parties.append(Party(name=name, role=role, address=address, tax_id=tax_id, representative=representative))


def _extract_party_b(text: str, match, parties: List[Party]):
    role = (match.group("role") or "Người lao động").strip() if match else "Người lao động"

    name = None
    address = None
    tax_id = None

    tail_start = max(0, len(text) * 3 // 4)
    tail = text[tail_start:]

    m = _EMPLOYEE_TABLE_RE.search(text)
    if m:
        name = m.group(1).strip()
        name = re.sub(r"\s*\|.*$", "", name).strip()

    m = _CMND_RE.search(text)
    if m:
        tax_id = m.group(1).strip()

    m = _ADDRESS_RE.search(tail)
    if not m:
        m = _ADDRESS_RE.search(text)
    if m:
        address = m.group(1).strip()
        address = re.sub(r"\s*\|.*$", "", address).strip()
        address = re.sub(r"^[:\|\s]+", "", address)

    if name:
        parties.append(Party(name=name, role=role, address=address, tax_id=tax_id))


# ============================================================
#  Nhóm 2: Hiệu lực & Thực thi
# ============================================================

_DATE_VI = r"\d{1,2}\s*(?:/|\.|\-|tháng)\s*\d{1,2}\s*(?:/|\.|\-|năm|$)\s*\d{2,4}"

_EXECUTION_PATTERNS = [
    r"(?:Hôm\s+nay|hôm\s+nay),\s*ngày\s+(" + _DATE_VI + ")",
    r"(?:ngày\s+ký|ký\s+kết|ngày\s+lập)\s*[:\-–]?\s*(" + _DATE_VI + ")",
]

_START_DATE_PATTERNS = [
    r"Từ\s+ngày\s*[:\|\t]+\s*(" + _DATE_VI + ")",
    r"(?:có\s+hiệu\s+lực|hiệu\s+lực)\s+(?:từ|kể\s+từ)\s+(?:ngày\s+)?(" + _DATE_VI + ")",
    r"bắt\s+đầu\s+(?:từ|kể\s+từ)\s+(?:ngày\s+)?(" + _DATE_VI + ")",
]

_END_DATE_PATTERNS = [
    r"Đến\s+ngày\s*[:\|\t]+\s*(" + _DATE_VI + ")",
    r"(?:đến|cho\s+đến)\s+(?:ngày\s+)?(" + _DATE_VI + ")",
    r"kết\s+thúc\s+(?:vào|ngày)\s+(" + _DATE_VI + ")",
]


def _extract_dates(text: str) -> dict:
    start_date = _find_first_match(text, _START_DATE_PATTERNS)
    end_date = _find_first_match(text, _END_DATE_PATTERNS)

    if not start_date:
        m = re.search(r"Từ\s+ngày\s*.*?(\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4})", text, re.IGNORECASE)
        if m:
            start_date = m.group(1).strip()

    if not end_date:
        m = re.search(r"Đến\s+ngày\s*.*?(\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4})", text, re.IGNORECASE)
        if m:
            end_date = m.group(1).strip()

    return {
        "execution_date": _find_first_match(text, _EXECUTION_PATTERNS),
        "start_date": start_date,
        "end_date": end_date,
    }


def _extract_force_majeure(text: str) -> Optional[str]:
    for kw in [r"bất\s+khả\s+kháng", r"force\s*majeure", r"sự\s+kiện\s+bất\s+khả\s+kháng"]:
        ctx = _extract_line_around(text, kw, context_lines=1)
        if ctx and len(ctx) > 10:
            return ctx
    return None


# ============================================================
#  Nhóm 3: Tài chính
# ============================================================

_VALUE_PATTERNS = [
    r"(?:Lương\s+căn\s+bản|Lương\s+cơ\s+bản|Mức\s+lương\s+căn\s+bản)\s*[:\|\t]+\s*\|?\s*(.+?)(?:\s*\||\s*\n|\s*$)",
    r"(?:giá\s+trị\s+hợp\s+đồng|tổng\s+giá\s+trị)\s*[:\-–]\s*(.+)",
    r"(?:thù\s+lao|tiền\s+công)\s*[:\-–]\s*(.+)",
]

_PAYMENT_METHOD_PATTERNS = [
    r"(?:Hình\s+thức\s+trả\s+lương|phương\s+thức\s+thanh\s+toán)\s*[:\|\t]+\s*\|?\s*(.+?)(?:\s*\||\s*\n|\s*$)",
    r"thanh\s+toán\s+bằng\s+(?:tiền\s+mặt|chuyển\s+khoản).*",
]

_PAYMENT_TERMS_PATTERNS = [
    r"(?:tiến\s+độ\s+thanh\s+toán|điều\s+khoản\s+thanh\s+toán)\s*[:\-–]?\s*(.+)",
]


def _extract_finance(text: str) -> dict:
    value = _find_first_match(text, _VALUE_PATTERNS)

    method = _find_first_match(text, _PAYMENT_METHOD_PATTERNS)
    if not method:
        ctx = _extract_line_around(text, r"trả\s+lương\s+vào\s+ngày", context_lines=0)
        if ctx:
            method = ctx

    terms = _find_first_match(text, _PAYMENT_TERMS_PATTERNS)
    if not terms:
        terms = _extract_line_around(text, r"thanh\s+toán\s+đầy\s+đủ", context_lines=0)

    return {
        "contract_value": value,
        "payment_method": method,
        "payment_terms": terms,
    }


# ============================================================
#  Nhóm 4: Vi phạm, Phạt & Giải quyết tranh chấp
# ============================================================


def _extract_termination(text: str) -> Optional[str]:
    for kw in [r"(?:Tạm\s+hoãn|tạm\s+hoãn).*chấm\s+dứt", r"chấm\s+dứt\s+hợp\s+đồng\s+lao\s+động", r"đơn\s+phương\s+chấm\s+dứt"]:
        ctx = _extract_line_around(text, kw, context_lines=1)
        if ctx and len(ctx) > 15 and "bồi thường" not in ctx.lower():
            return ctx
    return None


def _extract_penalty(text: str) -> dict:
    penalty = None
    for kw in [r"phạt\s+vi\s+phạm", r"mức\s+phạt", r"tiền\s+phạt"]:
        ctx = _extract_line_around(text, kw, context_lines=1)
        if ctx and len(ctx) > 10:
            penalty = ctx
            break

    indemnity = None
    for kw in [r"bồi\s+thường", r"bồi\s+hoàn", r"BỒI\s+THƯỜNG"]:
        ctx = _extract_line_around(text, kw, context_lines=1)
        if ctx and len(ctx) > 10 and (not penalty or ctx != penalty):
            indemnity = ctx
            break

    return {"penalty_clause": penalty, "indemnity": indemnity}


def _extract_dispute(text: str) -> Optional[str]:
    for kw in [
        r"(?:trọng\s+tài|tòa\s+án)\s+có\s+thẩm\s+quyền",
        r"giải\s+quyết\s+tranh\s+chấp",
    ]:
        ctx = _extract_line_around(text, kw, context_lines=1)
        if ctx and len(ctx) > 15:
            return ctx
    return None


# ============================================================
#  Nhóm 5: Điều khoản chung khác
# ============================================================


def _extract_governing_law(text: str) -> Optional[str]:
    for kw in [
        r"pháp\s+luật\s+lao\s+động",
        r"luật\s+áp\s+dụng",
        r"pháp\s+luật\s+(?:áp\s+dụng|điều\s+chỉnh|hiện\s+hành)",
    ]:
        ctx = _extract_line_around(text, kw, context_lines=0)
        if ctx and len(ctx) > 10:
            return ctx
    return None


def _extract_confidentiality(text: str) -> Optional[str]:
    for kw in [r"bảo\s+mật", r"bí\s+mật", r"confidential"]:
        ctx = _extract_line_around(text, kw, context_lines=0)
        if ctx and len(ctx) > 5:
            return ctx
    return None


def _extract_severability(text: str) -> Optional[str]:
    for kw in [
        r"độc\s+lập\s+của\s+điều\s+khoản",
        r"vô\s+hiệu\s+(?:từng|một)\s+phần",
        r"severab",
    ]:
        ctx = _extract_line_around(text, kw, context_lines=0)
        if ctx and len(ctx) > 10:
            return ctx
    return None


def _extract_amendments(text: str) -> Optional[str]:
    for kw in [
        r"sửa\s+đổi(?:\s+bổ\s+sung)?",
        r"phụ\s+lục\s+(?:sửa|hợp\s+đồng)",
    ]:
        ctx = _extract_line_around(text, kw, context_lines=1)
        if ctx and len(ctx) > 15:
            return ctx
    return None


# ============================================================
#  Loại hợp đồng
# ============================================================

_CONTRACT_TYPE_RE = re.compile(
    r"(?:HỢP\s+ĐỒNG|Hợp\s+đồng)\s+(?P<type>.+?)(?:\n|\(|$)",
    re.IGNORECASE,
)


def _extract_contract_type(text: str) -> Optional[str]:
    m = _CONTRACT_TYPE_RE.search(text)
    if m:
        ct = m.group("type").strip()
        if 3 < len(ct) < 120:
            return f"Hợp đồng {ct}"
    for kw in ["HỢP ĐỒNG LAO ĐỘNG", "HỢP ĐỒNG THƯƠNG MẠI", "HỢP ĐỒNG MUA BÁN",
               "HỢP ĐỒNG DỊCH VỤ", "HỢP ĐỒNG THUÊ", "HỢP ĐỒNG HỢP TÁC"]:
        if kw in text.upper():
            return kw.title()
    return None


# ============================================================
#  Trích xuất điều khoản
# ============================================================

_CLAUSE_SPLIT_RE = re.compile(
    r"(?:^|\n)\s*(Điều|ĐIỀU)\s+(\d+)\s*[\.:\)\-\–]\s*",
    re.MULTILINE,
)


def _extract_clauses(text: str) -> List[Clause]:
    clauses = []
    splits = list(_CLAUSE_SPLIT_RE.finditer(text))

    for i, match in enumerate(splits):
        number = match.group(2)
        header_end = match.end()
        next_start = splits[i + 1].start() if i + 1 < len(splits) else len(text)
        content = text[header_end:next_start].strip()

        lines = [l.strip() for l in content.split("\n") if l.strip()]
        title = lines[0][:150] if lines else None

        body = _normalize("\n".join(lines))
        if body.startswith("- "):
            body = body[2:]

        clauses.append(Clause(clause_number=number, title=title, summary=body))

    return clauses


# ============================================================
#  Hàm chính
# ============================================================


def parse_contract(text: str, contract_id: str) -> ContractAnalysis:
    logger.info(f"Parsing contract {contract_id} with rule-based extractor")
    text = unicodedata.normalize("NFC", text)

    dates = _extract_dates(text)
    finance = _extract_finance(text)
    penalty = _extract_penalty(text)

    return ContractAnalysis(
        contract_id=contract_id,
        contract_type=_extract_contract_type(text),
        parties=_extract_parties(text),
        execution_date=dates.get("execution_date"),
        start_date=dates.get("start_date"),
        end_date=dates.get("end_date"),
        duration=None,
        contract_value=finance.get("contract_value"),
        payment_terms=finance.get("payment_terms"),
        payment_method=finance.get("payment_method"),
        termination_clause=_extract_termination(text),
        penalty_clause=penalty.get("penalty_clause"),
        indemnity=penalty.get("indemnity"),
        force_majeure=_extract_force_majeure(text),
        governing_law=_extract_governing_law(text),
        dispute_resolution=_extract_dispute(text),
        confidentiality=_extract_confidentiality(text),
        severability=_extract_severability(text),
        amendments=_extract_amendments(text),
        clauses=_extract_clauses(text),
    )
