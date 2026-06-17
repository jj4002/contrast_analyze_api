"""
Data Cleaner — Sửa dữ liệu lỗi trước khi vào DB.

Triết lý:
- Cố gắng sửa (repair) dữ liệu lỗi bằng cách trích xuất từ các nguồn khác
- KHÔNG bịa ra dữ liệu không có thật
- Nếu không sửa được → skip hoặc giữ nguyên, không tạo giả

Các kiểu sửa:
1. Title rỗng/rác → thử extract từ content, URL
2. Số hiệu thiếu → thử extract từ content, URL
3. Date sai format → sửa format
4. Status → chỉ infer nếu có bằng chứng rõ ràng trong content
"""
import re
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

MIN_CONTENT_LENGTH = 200

GARBAGE_TITLE_PATTERNS = [
    r"không có tiêu đề",
    r"không trích xuất được",
    r"just a moment",
    r"attention required",
    # Title bị lấy nhầm header văn bản
    r"CỘNG\s*HÒA\s*XÃ\s*HỘI\s*CHỦ\s*NGHĨA",
    r"Độc\s*lập\s*[-–]\s*Tự\s*do\s*[-–]\s*Hạnh\s*phúc",
    r"CONG\s*HOA\s*XA\s*HOI\s*CHU\s*NGHIA",
    r"Doc\s*lap\s*[-–]\s*Tu\s*do\s*[-–]\s*Hanh\s*phuc",
    # Dòng bắt đầu bằng ký tự đặc biệt
    r"^[\s\-\\*|_]+",
]

CLOUDFLARE_PATTERNS = [
    r"just a moment\.\.\.",
    r"checking your browser",
    r"challenges\.cloudflare\.com",
]

ENCODING_GARBAGE = [
    "\ufffd", "\x86", "\x81",
]

# ── Public API ────────────────────────────────────────────────────────────


def fix_doc_number(
    doc_number: Optional[str],
    content: Optional[str] = None,
    url: Optional[str] = None,
) -> Optional[str]:
    """Sửa số hiệu văn bản bị thiếu.

    Chiến lược:
    1. Nếu có doc_number → làm sạch
    2. Nếu thiếu → thử extract từ content (dòng đầu chứa "số")
    3. Nếu content cũng không → thử extract từ URL
    """
    if doc_number:
        doc_number = doc_number.strip()
        doc_number = re.sub(r"\s+", " ", doc_number)
        doc_number = re.sub(r"[\ufeff\u200b]", "", doc_number)
        clean = re.sub(r"[^\w\/\.\-]", "", doc_number).strip()
        clean = re.sub(r"\-{2,}", "-", clean)
        clean = re.sub(r"\/{2,}", "/", clean)
        if clean:
            return clean

    logger.warning(f"[Cleaner] Doc number missing, trying repair...")

    # Thử extract từ content: "Số: 45/2019/QH14" hoặc "Số hiệu: 45/2019/QH14"
    if content:
        m = re.search(r"(?:số|số hiệu|số ký hiệu)\s*:\s*([\w\/\.\-]+)", content, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            if re.search(r"\d+", candidate):
                logger.info(f"[Cleaner] Repaired doc number from content: {candidate}")
                return candidate

    # Thử từ URL: /Nghi-dinh-168-2024-ND-CP-xxx.aspx → 168/2024/NĐ-CP
    if url:
        slug = url.rstrip("/").split("/")[-1]
        m = re.match(r".*?(\d{2,})[-\s]*(\d{4})[-\s]*([A-ZĐ]{2,})[-\s]*([A-Z]+)", slug)
        if m:
            candidate = f"{m.group(1)}/{m.group(2)}/{m.group(3)}-{m.group(4)}"
            logger.info(f"[Cleaner] Repaired doc number from URL: {candidate}")
            return candidate
        # Simpler: just find "XXX/YYYY/XX-XX" pattern
        m = re.search(r"(\d+)[-](\d{4})[-]([A-ZĐ]+)[-]([A-Z]+)", slug)
        if m:
            candidate = f"{m.group(1)}/{m.group(2)}/{m.group(3)}-{m.group(4)}"
            logger.info(f"[Cleaner] Repaired doc number from URL: {candidate}")
            return candidate

    return None

DOC_TYPE_KEYWORDS = [
    (r"(?i)b[ôo]\s*lu[âa]t", "Bộ luật"),
    (r"(?i)lu[âa]t\b", "Luật"),
    (r"(?i)ngh[iị]\s*quy[eê]t", "Nghị quyết"),
    (r"(?i)ph[áa]p\s*l[êe]nh", "Pháp lệnh"),
    (r"(?i)ngh[iị]\s*[đd]inh", "Nghị định"),
    (r"(?i)quy[eê]t\s*[đd]inh", "Quyết định"),
    (r"(?i)th[oô]ng\s*t[ưu]", "Thông tư"),
    (r"(?i)ch[iỉ]\s*th[iị]", "Chỉ thị"),
    (r"(?i)c[oô]ng\s*v[aă]n", "Công văn"),
    (r"(?i)th[oô]ng\s*b[áa]o", "Thông báo"),
    (r"(?i)h[ưu]ớng\s*d[aaã]?n", "Hướng dẫn"),
    (r"(?i)quy\s*[đd]ịnh", "Quy định"),
    (r"(?i)quy\s*ch[eế]", "Quy chế"),
    (r"(?i)k[eế]\s*ho[ạ]ch", "Kế hoạch"),
    (r"(?i)ti[êe]u\s*chu[à]?[âa]?n", "Tiêu chuẩn Việt Nam (TCVN)"),
    (r"(?i)TCVN\b", "Tiêu chuẩn Việt Nam (TCVN)"),
    (r"(?i)QCVN\b", "Quy chuẩn Quốc gia (QCVN)"),
]

def fix_doc_type(
    doc_type: Optional[str],
    title: Optional[str] = None,
    url: Optional[str] = None,
) -> Optional[str]:
    """Sửa loại văn bản từ URL slug hoặc title nếu parser không lấy được.

    URL slug: 'Bo-luat-Lao-dong-2019' → 'Bộ luật'
    Title:    'Bộ luật Lao động 2019' → 'Bộ luật'
    """
    if doc_type and doc_type.strip():
        return doc_type.strip()

    candidates = []

    # URL slug (filename không có đuôi)
    if url:
        slug = url.rstrip("/").split("/")[-1].replace(".aspx", "").replace(".html", "")
        slug = slug.replace("-", " ").replace("_", " ")
        # Xoá số ID cuối: "Bo luat Lao dong 2019 333670" → "Bo luat Lao dong 2019"
        slug = re.sub(r"\s+\d{5,}$", "", slug).strip()
        candidates.append(slug)

    # Title hoặc slug làm candidates
    if title:
        candidates.append(title)

    for text in candidates:
        if not text:
            continue
        text_lower = text.lower().replace("-", " ")
        for pattern, label in DOC_TYPE_KEYWORDS:
            if re.search(pattern, text_lower):
                return label

    return None

def fix_date(date_str: Optional[str]) -> Optional[str]:
    """Sửa date string về ISO format (YYYY-MM-DD) cho SQLite date().

    Không bịa: nếu chỉ có năm → giữ năm, không thêm ngày/tháng giả.
    """
    if not date_str or not date_str.strip():
        return None

    date_str = date_str.strip()

    m = re.search(r"(\d{1,4})[/\-\.](\d{1,2})[/\-\.](\d{1,4})", date_str)
    if not m:
        m2 = re.search(r"\b(19\d{2}|20\d{2})\b", date_str)
        if m2:
            return m2.group(1)
        return date_str

    d1, d2, d3 = m.group(1), m.group(2), m.group(3)

    try:
        if len(d1) == 4:
            dt = datetime.strptime(f"{d1}-{d2}-{d3}", "%Y-%m-%d")
        elif len(d3) == 4:
            dt = datetime.strptime(f"{d3}-{d2}-{d1}", "%Y-%m-%d")
        else:
            return date_str
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_str

def validate_content(content: Optional[str], url: Optional[str] = None) -> bool:
    """Kiểm tra content có phải là nội dung thật không (tránh lưu rác)."""
    if not content or not content.strip():
        return False

    content_lower = content.lower()

    if len(content.strip()) < MIN_CONTENT_LENGTH:
        logger.warning(f"[Cleaner] Content too short ({len(content)} chars)")
        return False

    for pat in CLOUDFLARE_PATTERNS:
        if re.search(pat, content_lower):
            return False

    for ch in ENCODING_GARBAGE:
        if ch in content:
            logger.warning(f"[Cleaner] Encoding error in content")
            return False

    return True

def try_fix_encoding(text: str) -> str:
    """Thử fix encoding nếu có ký tự lỗi."""
    if "\ufffd" not in text:
        return text
    # Thử decode lại với windows-1252 → utf-8
    try:
        raw = text.encode("raw_unicode_escape")
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return text

def fix_category(
    category: Optional[str],
    title: Optional[str] = None,
    content: Optional[str] = None,
    url: Optional[str] = None,
    doc_id: str = "",
) -> Optional[str]:
    """Sửa category từ URL/title nếu parser không lấy được.

    Dùng detect_category của metadata_extractor (rule-based).
    """
    if category and category.strip():
        return category.strip()

    from helpers.metadata_extractor import detect_category
    detected = detect_category(title=title or "")
    return detected if detected != "khác" else None

def clean_document(raw: Dict) -> Dict:
    """Sửa toàn bộ document trước khi insert (schema v2).

    Input: dict từ parser
    Output: dict đã sửa + _skip flag
    """
    cleaned = dict(raw)

    content = raw.get("content", "")
    url = raw.get("url")
    content = try_fix_encoding(content)
    content = re.sub(r"[\ufeff\u200b\u200c\u200d]", "", content)
    content = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", content)
    cleaned["content"] = content.strip()

    if not validate_content(content, url=url):
        cleaned["_skip"] = True
        return cleaned

    cleaned["title"] = raw.get("title", "Văn bản pháp luật")
    cleaned["doc_number"] = fix_doc_number(raw.get("doc_number"), content=content, url=url)
    cleaned["doc_type"] = fix_doc_type(raw.get("doc_type"), title=cleaned["title"], url=url)
    cleaned["category"] = fix_category(
        raw.get("category"), title=cleaned["title"], content=content, url=url, doc_id=raw.get("doc_id", ""),
    )
    cleaned["issued_date"] = fix_date(raw.get("issued_date"))
    cleaned["effective_date"] = fix_date(raw.get("effective_date"))
    cleaned["expiry_date"] = fix_date(raw.get("expiry_date"))

    # Year published từ issued_date (ISO: YYYY-MM-DD)
    if not cleaned.get("year_published") and cleaned.get("issued_date"):
        m = re.search(r"(\d{4})", cleaned["issued_date"])
        if m:
            cleaned["year_published"] = int(m.group(1))

    cleaned["_skip"] = False
    return cleaned

