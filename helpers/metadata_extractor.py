"""
Metadata Extractor — Rule-based, không cần Gemini.

Thay thế _extract_document_metadata() và _extract_query_keywords() cũ.
Chạy local, nhanh, không tốn API quota.
"""
import re
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse
from config import DOC_NUMBER_RE as _CONFIG_DOC_NUMBER_RE

logger = logging.getLogger(__name__)

# ── Vietnamese stopwords ──────────────────────────────────────────────────

STOPWORDS = {
    "và", "của", "các", "có", "được", "cho", "trong", "với", "hoặc",
    "không", "theo", "tại", "về", "đến", "là", "này", "một", "những",
    "đã", "sẽ", "đang", "bị", "phải", "khi", "để", "từ", "ra", "lên",
    "xuống", "vào", "ở", "trên", "dưới", "cùng", "đều", "hay", "nếu",
    "thì", "do", "vì", "nên", "mà", "còn", "đây", "đó", "ấy", "nào",
    "sao", "thế", "vậy", "như", "cũng", "vẫn", "chỉ", "đã", "rất",
    "quá", "lắm", "hơn", "kém", "được", "bằng", "nhưng", "tuy", "nhiên",
    "mặc dù", "song", "và", "với", "cả", "hết", "gì", "hãy", "chớ",
    "đừng", "xin", "vui lòng", "nên", "cần", "phải", "hãy",
    "số", "ngày", "tháng", "năm", "điều", "khoản", "chương", "mục",
}

# ── Category detection ────────────────────────────────────────────────────

TITLE_KEYWORDS_MAP = [
    (r"hình\s*sự", "hình sự"),
    (r"hành\s*chính", "hành chính"),
    (r"dân\s*sự", "dân sự"),
    (r"tố\s*tụng", "tố tụng"),
    (r"tư\s*pháp", "tư pháp - hộ tịch"),
    (r"hộ\s*tịch", "tư pháp - hộ tịch"),
    (r"quốc\s*phòng", "quốc phòng - an ninh"),
    (r"an\s*ninh", "quốc phòng - an ninh"),
    (r"doanh\s*nghiệp", "doanh nghiệp"),
    (r"đầu\s*tư", "đầu tư"),
    (r"thương\s*mại", "thương mại"),
    (r"tài\s*chính", "tài chính - ngân hàng"),
    (r"ngân\s*hàng", "tài chính - ngân hàng"),
    (r"thuế", "thuế - phí - lệ phí"),
    (r"phí\s*lệ\s*phí", "thuế - phí - lệ phí"),
    (r"kế\s*toán", "kế toán - kiểm toán"),
    (r"kiểm\s*toán", "kế toán - kiểm toán"),
    (r"xuất\s*nhập\s*khẩu", "xuất nhập khẩu - hải quan"),
    (r"hải\s*quan", "xuất nhập khẩu - hải quan"),
    (r"sở\s*hữu\s*trí\s*tuệ", "sở hữu trí tuệ"),
    (r"lao\s*động", "lao động - tiền lương"),
    (r"tiền\s*lương", "lao động - tiền lương"),
    (r"bảo\s*hiểm", "bảo hiểm"),
    (r"y\s*tế", "y tế - sức khỏe"),
    (r"sức\s*khỏe", "y tế - sức khỏe"),
    (r"giáo\s*dục", "giáo dục - đào tạo"),
    (r"đào\s*tạo", "giáo dục - đào tạo"),
    (r"văn\s*hóa", "văn hóa - thể thao - du lịch"),
    (r"thể\s*thao", "văn hóa - thể thao - du lịch"),
    (r"du\s*lịch", "văn hóa - thể thao - du lịch"),
    (r"cán\s*bộ", "cán bộ - công chức - viên chức"),
    (r"công\s*chức", "cán bộ - công chức - viên chức"),
    (r"viên\s*chức", "cán bộ - công chức - viên chức"),
    (r"đất\s*đai", "đất đai - nhà ở"),
    (r"nhà\s*ở", "đất đai - nhà ở"),
    (r"xây\s*dựng", "xây dựng - đô thị"),
    (r"đô\s*thị", "xây dựng - đô thị"),
    (r"giao\s*thông", "giao thông - vận tải"),
    (r"vận\s*tải", "giao thông - vận tải"),
    (r"tài\s*nguyên", "tài nguyên - môi trường"),
    (r"môi\s*trường", "tài nguyên - môi trường"),
    (r"nông\s*nghiệp", "nông nghiệp - lâm nghiệp - thủy sản"),
    (r"lâm\s*nghiệp", "nông nghiệp - lâm nghiệp - thủy sản"),
    (r"thủy\s*sản", "nông nghiệp - lâm nghiệp - thủy sản"),
    (r"công\s*nghệ\s*thông\s*tin", "công nghệ thông tin - an ninh mạng"),
    (r"an\s*ninh\s*mạng", "công nghệ thông tin - an ninh mạng"),
    (r"cư\s*trú", "cư trú"),
]

# ── Header / Footer extraction ───────────────────────────────────────────

STOP_HEADER_PATTERNS = [
    r"QUYẾT ĐỊNH:",
    r"Điều\s+1\b",
    r"CHƯƠNG\s+I\b",
]

EFFECTIVE_KEYWORDS = [
    # "có hiệu lực thi hành"
    "có hiệu lực thi hành",
    "hiệu lực thi hành",
    # "có hiệu lực kể từ ngày..."
    "có hiệu lực kể từ ngày",
    "có hiệu lực từ ngày",
    "có hiệu lực sau",
    "có hiệu lực vào",
    "thông qua",
    "thông qua ngày",
    # "kể từ ngày ký" — fallback dùng issued_date
    "kể từ ngày ký",
    "kể từ ngày ký ban hành",
    "kể từ ngày ban hành",
    "từ ngày ký",
    "ngày ký ban hành",
    # "bắt đầu có hiệu lực"
    "bắt đầu có hiệu lực",
    "bắt đầu thi hành",
    "thi hành kể từ ngày",
    "thi hành từ ngày",
]

# Keywords dùng để tìm paragraph chứa thông tin hết hiệu lực (fallback cho extract_expiry_date)
# CHÚ Ý: Không dùng "đến trước ngày", "đến ngày" — chúng xuất hiện trong "Điều khoản chuyển tiếp"
# (deadline nội bộ, không phải hết hiệu lực của văn bản)
EXPIRY_KEYWORDS = [
    "hết hiệu lực",
    "đến hết ngày",
    "hết hiệu lực thi hành",
]

# Pattern phát hiện "có hiệu lực kể từ ngày ký" → dùng issued_date
SIGNING_DATE_EFFECTIVE_PATTERNS = [
    r"có\s+hiệu\s+lực\s+(?:thi\s+hành\s+)?kể\s+từ\s+ngày\s+ký",
    r"có\s+hiệu\s+lực\s+(?:thi\s+hành\s+)?từ\s+ngày\s+ký",
    r"hiệu\s+lực\s+thi\s+hành\s+kể\s+từ\s+ngày\s+ký",
    r"có\s+hiệu\s+lực\s+kể\s+từ\s+ngày\s+ban\s+hành",
    r"có\s+hiệu\s+lực\s+từ\s+ngày\s+ban\s+hành",
    r"có\s+hiệu\s+lực\s+thi\s+hành\s+kể\s+từ\s+ngày\s+ký\s+ban\s+hành",
    r"có\s+hiệu\s+lực\s+thi\s+hành\s+từ\s+ngày\s+ký\s+ban\s+hành",
]

# Pattern bắt ngày trong text (dd/mm/yyyy, dd-mm-yyyy, ngày dd tháng mm năm yyyy)
DATE_PATTERNS = [
    # "ngày 15 tháng 3 năm 2024" hoặc "01 tháng 7 năm 2026" (thiếu 'ngày')
    r"(?:ngày\s+)?(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
    # "15/03/2024" hoặc "15-03-2024"
    r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})",
    # "2024-03-15"
    r"(\d{4})-(\d{1,2})-(\d{1,2})",
]

# ── Relation extraction patterns ─────────────────────────────────────────

# Patterns phát hiện văn bản bị bãi bỏ/thay thế
# Match: "Bãi bỏ Quyết định số 12/2020/QĐ-UBND", "thay thế Nghị định 168/2024/NĐ-CP"
_DOC_NUMBER_RE = _CONFIG_DOC_NUMBER_RE

# Patterns phát hiện quan hệ TOÀN BỘ (replaces/abolishes)
# Mỗi pattern có thêm capture group optional cho issuing_authority:
#   group(1) = doc_number, group(2) = "UBND thành phố Đà Nẵng" (nếu có)
_RE_AUTH = r"(?:\s+của\s+([^,;.\n]+?))?"
RELATION_PATTERNS = [
    # "Bãi bỏ [loại văn bản] số X [của Authority]"
    (r"[Bb]ãi\s+bỏ\s+(?:toàn\s+bộ\s+)?(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH, "abolishes"),
    # "Thay thế [loại văn bản] số X [của Authority]"
    (r"[Tt]hay\s+thế\s+(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH, "replaces"),
    # "thay thế:" + newline + bullet + doc_number (multi-line)
    (r"[Tt]hay\s+thế\s*:\s*\n\s*[-–•]\s*(?:[\wĐđ]+\s+){0,5}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH, "replaces"),
    # "Hết hiệu lực [loại văn bản] số X [của Authority]"
    (r"[Hh]ết\s+hiệu\s+lực\s+(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH, "abolishes"),
    # "[VB] số X hết hiệu lực [của Authority]"
    (r"(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")\s+hết\s+hiệu\s+lực" + _RE_AUTH, "abolishes"),
    # "Sửa đổi, bổ sung [loại văn bản] số X [của Authority]" — toàn bộ văn bản
    (r"[Ss]ửa\s+đổi[,\s]+bổ\s+sung\s+(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH, "amends"),
    # "ban hành kèm theo [VB] số X [của Authority]"
    (r"ban\s+hành\s+kèm\s+theo\s+(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH, "amends"),
    # "Phụ lục kèm theo [VB] số X [của Authority]" (không có "ban hành")
    (r"(?:phụ\s+lục\s+)?kèm\s+theo\s+(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH, "amends"),
]

# Patterns phát hiện sửa đổi/bãi bỏ MỘT PHẦN (điều khoản cụ thể)
# → relation_type = "amends_partial"
# Capture: (doc_number, provision_text)
PARTIAL_AMEND_PATTERNS = [
    # "Bãi bỏ khoản X Điều Y của [văn bản] số Z [của Authority]"
    (
        r"[Bb]ãi\s+bỏ\s+((?:khoản|điểm|mục)\s+[\wĐđ\d]+(?:[,\s]+(?:khoản|điểm|mục)\s+[\wĐđ\d]+)*"
        r"(?:\s+(?:Điều|điều)\s+[\d\w]+)?)\s+(?:của\s+)?(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH,
        "amends_partial",
    ),
    # "Sửa đổi Điều X, khoản Y của [văn bản] số Z [của Authority]"
    (
        r"[Ss]ửa\s+đổi\s+((?:Điều|điều|khoản|điểm)\s+[\d\w]+(?:[,\s]+(?:Điều|điều|khoản|điểm)\s+[\d\w]+)*)"
        r"\s+(?:của\s+)?(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH,
        "amends_partial",
    ),
    # "Bổ sung Điều X vào [văn bản] số Z [của Authority]"
    (
        r"[Bb]ổ\s+sung\s+((?:Điều|điều|khoản|điểm)\s+[\d\w]+(?:[,\s]+(?:Điều|điều|khoản|điểm)\s+[\d\w]+)*)"
        r"\s+(?:vào\s+)?(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH,
        "amends_partial",
    ),
    # TVPL style: "Sửa đổi, bổ sung [provisions] ban hành kèm theo [VB] số X [của Authority]"
    (
        r"[Ss]ửa\s+đổi[,\s]+bổ\s+sung\s+"
        r"((?:các\s+)?(?:thủ\s+tục\s+hành\s+chính|nội\s+dung)\s+"
        r"(?:nêu\s+tại\s+)?[\w\d,.\s_\-\/]+?)"
        r"\s+ban\s+hành\s+kèm\s+theo\s+(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(" + _DOC_NUMBER_RE + r")" + _RE_AUTH,
        "amends_partial",
    ),
]


def extract_header_section(content: str) -> str:
    """Cắt phần đầu văn bản chứa 'Danh mục / Lĩnh vực'.

    Bắt đầu từ sau 'Số hiệu', dừng ở 'QUYẾT ĐỊNH:', 'Điều 1.' hoặc 'CHƯƠNG I'.
    Kết quả ~100-200 chữ chứa trích yếu + căn cứ pháp lý.
    """
    if not content:
        return ""

    so_hieu_match = re.search(r"Số\s*hiệu", content)
    start = so_hieu_match.end() if so_hieu_match else 0

    stop_pos = len(content)
    for pat in STOP_HEADER_PATTERNS:
        m = re.search(pat, content[max(start, 0):])
        if m:
            stop_pos = start + m.start()
            break

    header = content[start:stop_pos].strip()
    header = re.sub(r"\s+", " ", header)
    if len(header) > 500:
        header = header[:500]
    return header


# ── Enforce Article Finder ──────────────────────────────────────────

def _find_article_with_keywords(content: str, keywords: List[str]) -> Optional[str]:
    """Tìm điều khoản chứa enforcement keywords trong content không có paragraph break.

    Quét các dòng bắt đầu bằng "Điều" hoặc "**Điều", tìm Điều có chứa keyword hiệu lực.
    Nếu tìm thấy, trả về tất cả nội dung từ Điều đó đến Điều tiếp theo (hoặc hết content).
    """
    lines = content.split("\n")
    effective_indices = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        stripped_clean = stripped.strip("*_").strip()
        if re.match(r"Điều\s+[\dIVXLCH]+", stripped_clean):
            effective_indices.append(i)

    if not effective_indices:
        return None

    # Trong mỗi Điều, kiểm tra xem có keyword hiệu lực không
    for idx, start_i in enumerate(effective_indices):
        next_i = effective_indices[idx + 1] if idx + 1 < len(effective_indices) else len(lines)
        article_lines = lines[start_i:next_i]
        article_text = "\n".join(article_lines).lower()
        for kw in keywords:
            if kw in article_text:
                # Trả về nội dung Điều ± 3 dòng context
                ctx_start = max(0, start_i - 1)
                ctx_end = min(len(lines), next_i + 1)
                return "\n".join(lines[ctx_start:ctx_end])
    return None


def _find_effective_article(content: str) -> Optional[str]:
    """Tìm Điều 'Hiệu lực thi hành' trong content.

    Quét các dòng chứa 'Điều', kiểm tra 5 dòng tiếp theo
    có chứa keyword 'hiệu lực' hoặc 'thi hành' không.
    Trả về nội dung paragraph của Điều đó.

    Returns:
        Nội dung paragraph chứa thông tin hiệu lực, hoặc None.
    """
    if not content:
        return None
    lines = content.split("\n")
    found_article_start = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        stripped_clean = stripped.strip("*_").strip()
        # Match "Điều X." or "Điều X:" header
        if re.match(r"Điều\s+[\dIVXLCH]+\s*[\.:]", stripped_clean):
            # Check this line + next 5 lines for enforcement keywords
            window = " ".join(
                l.strip().strip("*_").strip()
                for l in lines[i:i+6] if l.strip()
            )
            if re.search(r"[Hh]iệu\s+lực|thi\s+hành", window):
                found_article_start = i
                break

    if found_article_start < 0:
        return None

    # Collect paragraphs up to next "Điều" or "Chương" or end
    result_lines: List[str] = []
    for line in lines[found_article_start:]:
        stripped = line.strip()
        if not stripped:
            continue
        stripped_clean = stripped.strip("*_").strip()
        # Stop at next "Điều" or "Chương"
        if re.match(r"(Điều|Chương|Phần|Mục)\s+[\dIVXLCH]", stripped_clean):
            if result_lines:  # Already collected something
                break
        result_lines.append(stripped)

    return "\n".join(result_lines) if result_lines else None


def extract_effective_date_section(content: str) -> str:
    """Móc phần đuôi văn bản chứa thông tin ngày hiệu lực.

    Quét từ dưới lên, tìm đoạn chứa các keyword hiệu lực.
    Nếu paragraph quá lớn (document không có paragraph break — thường từ luatvietnam),
    thử dùng _find_effective_article để narrow down phần enforcement.
    """
    if not content:
        return ""

    paragraphs = re.split(r"\n\s*\n", content)
    for para in reversed(paragraphs):
        para_stripped = para.strip()
        if not para_stripped:
            continue
        para_lower = para_stripped.lower()
        for kw in EFFECTIVE_KEYWORDS:
            if kw in para_lower:
                # Nếu paragraph là toàn bộ document (>2000 chars, không có paragraph break),
                # thử narrow down về enforcement article thực sự để tránh false positive
                # "đến hết ngày" từ các phần không liên quan (điều khoản chuyển tiếp, thời kỳ kiểm tra...)
                if len(para_stripped) > 2000:
                    narrowed = _find_effective_article(para_stripped)
                    if narrowed:
                        return narrowed
                    # Fallback: quét các dòng bắt đầu bằng "Điều", tìm dòng có effective keywords
                    narrowed = _find_article_with_keywords(para_stripped, EFFECTIVE_KEYWORDS)
                    if narrowed:
                        return narrowed
                return para_stripped
    return ""


def is_effective_from_signing(content: str) -> bool:
    """Kiểm tra văn bản có dùng cụm "có hiệu lực kể từ ngày ký" không.

    Nếu có → effective_date = issued_date.
    """
    if not content:
        return False
    text_lower = content.lower()
    for pat in SIGNING_DATE_EFFECTIVE_PATTERNS:
        if re.search(pat, text_lower):
            return True
    return False


def _calc_effective_from_signing_delay(
    content: str,
    issued_date: Optional[str] = None,
) -> Optional[str]:
    """Kiểm tra pattern 'sau X ngày kể từ ngày ký ban hành' → issued_date + X days.

    Ví dụ: "Thông tư này có hiệu lực thi hành sau 45 ngày kể từ ngày ký ban hành"
    → issued_date + 45 ngày.
    """
    if not content or not issued_date:
        return None

    text_lower = content.lower()
    # "sau 45 ngày kể từ ngày ký ban hành" hoặc "sau 45 ngày kể từ ngày ký"
    delay_pat = r"sau\s+(\d+)\s+ngày\s+kể\s+từ\s+ngày\s+ký\s*(?:ban\s+hành)?"
    m = re.search(delay_pat, text_lower)
    if not m:
        return None

    days = int(m.group(1))
    iso_date = _normalize_to_iso(issued_date)
    if not iso_date:
        return None

    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        result = dt + timedelta(days=days)
        return result.strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_vietnamese_date(text: str) -> Optional[str]:
    """Parse 1 ngày từ text Việt Nam → YYYY-MM-DD.

    Hỗ trợ:
    - "ngày 15 tháng 3 năm 2024"
    - "15/03/2024", "15-03-2024"
    - "2024-03-15"
    """
    if not text:
        return None

    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if not m:
            continue
        try:
            groups = m.groups()
            if len(groups) == 3:
                # Heuristic: YYYY luôn là 4 chữ số
                if len(groups[0]) == 4:
                    # YYYY-MM-DD
                    y, mo, d = groups
                else:
                    # dd-mm-yyyy
                    d, mo, y = groups
                d = int(d)
                mo = int(mo)
                y = int(y)
                if 1 <= d <= 31 and 1 <= mo <= 12 and 1900 <= y <= 2100:
                    return f"{y:04d}-{mo:02d}-{d:02d}"
        except (ValueError, IndexError):
            continue
    return None


def _extract_date_from_text(text: str, patterns: List[str]) -> Optional[str]:
    """Helper: thử các after_kw_patterns trên 1 text → parse date."""
    text_lower = text.lower()
    for pat in patterns:
        m = re.search(pat, text_lower)
        if m:
            candidate = m.group(1)[:80]
            parsed = parse_vietnamese_date(candidate)
            if parsed:
                return parsed
    return None


def extract_effective_date(
    content: str,
    issued_date: Optional[str] = None,
) -> Optional[str]:
    """Trích xuất effective_date (YYYY-MM-DD) từ content (sync, không DB).

    Logic:
    1. Tìm Điều 'Hiệu lực thi hành' → thử after_kw_patterns
    2. Fallback: section-based (extract_effective_date_section) + after_kw_patterns
    3. "kể từ ngày ký" → dùng issued_date
    4. None

    Cross-reference (dẫn chiếu VB khác) cần DB lookup → xử lý ở caller.
    Dùng find_cross_ref_doc_number() để lấy doc_number rồi tra cứu async.

    Args:
        content: nội dung văn bản
        issued_date: ngày ký/ban hành (YYYY-MM-DD hoặc DD/MM/YYYY) — fallback

    Returns:
        YYYY-MM-DD string hoặc None
    """
    article_content = _find_effective_article(content)
    section = extract_effective_date_section(content)

    after_kw_patterns = [
        r"có\s+hiệu\s+lực\s+thi\s+hành\s+kể\s+từ\s+ngày\s+([^.,;\n]+)",
        r"có\s+hiệu\s+lực\s+thi\s+hành\s+từ\s+ngày\s+([^.,;\n]+)",
        r"có\s+hiệu\s+lực\s+(?:thi\s+hành\s+)?(?:kể\s+từ\s+|từ\s+|vào\s+)?ngày\s+([^.,;\n]+)",
        r"hiệu\s+lực\s+thi\s+hành\s+(?:kể\s+từ\s+|từ\s+)?ngày\s+([^.,;\n]+)",
        r"thi\s+hành\s+(?:kể\s+từ\s+|từ\s+)?ngày\s+([^.,;\n]+)",
        # Hiến pháp: "thông qua ngày DD tháng MM năm YYYY"
        r"thông\s+qua\s+ngày\s+([^.,;\n]+)",
    ]

    # Case 1: Điều "Hiệu lực thi hành" (ưu tiên)
    if article_content:
        article_ref = find_cross_ref_doc_number(article_content)
        if not article_ref:
            parsed = _extract_date_from_text(article_content, after_kw_patterns)
            if parsed:
                return parsed
        if is_effective_from_signing(article_content):
            return _normalize_to_iso(issued_date)
        delay = _calc_effective_from_signing_delay(article_content, issued_date)
        if delay:
            return delay

    # Case 2: Section fallback
    if section:
        section_ref = find_cross_ref_doc_number(section)
        if not section_ref:
            parsed = _extract_date_from_text(section, after_kw_patterns)
            if parsed:
                return parsed
        if is_effective_from_signing(section):
            return _normalize_to_iso(issued_date)
        delay = _calc_effective_from_signing_delay(section, issued_date)
        if delay:
            return delay

    # Case 3: "ngày ký" trên toàn content
    if is_effective_from_signing(content):
        return _normalize_to_iso(issued_date)
    # Case 4: "sau X ngày kể từ ngày ký" trên toàn content
    delay = _calc_effective_from_signing_delay(content, issued_date)
    if delay:
        return delay

    return None


def find_cross_ref_doc_number(text: str) -> Optional[str]:
    """Kiểm tra text có chứa dẫn chiếu VB khác không.

    Pattern: "kể từ ngày [VB] số X ... có hiệu lực"
    Trả về doc_number của VB được dẫn chiếu (vd: "20/2026/NQ-CP").
    Dùng để tra cứu async DB ở caller.
    """
    if not text:
        return None
    text_lower = text.lower()
    cross_ref_patterns = [
        r"kể\s+từ\s+ngày\s+(?:[\wĐđ]+\s+){1,5}số\s+(" + _DOC_NUMBER_RE + r")\s+.*?có\s+hiệu\s+lực",
        r"từ\s+ngày\s+(?:[\wĐđ]+\s+){1,5}số\s+(" + _DOC_NUMBER_RE + r")\s+.*?có\s+hiệu\s+lực",
        r"kể\s+từ\s+ngày\s+(?:[\wĐđ]+\s+){1,5}số\s+(" + _DOC_NUMBER_RE + r")",
    ]
    for pat in cross_ref_patterns:
        m = re.search(pat, text_lower)
        if m:
            ref_number = m.group(1).strip().rstrip("-/")
            if ref_number and len(ref_number) >= 5:
                return ref_number
    return None


# Expiry patterns: narrow — luôn an toàn (chỉ match khi có "hết hiệu lực" hoặc "đến hết ngày")
# Strict patterns — chỉ match "hết hiệu lực" (safe khi không có enforcement context)
_EXPIRY_STRICT_PATTERNS = [
    r"hết\s+hiệu\s+lực\s+(?:thi\s+hành\s+)?(?:kể\s+từ\s+)?ngày\s+(\d{1,2}\s*[/\-]\s*\d{1,2}\s*[/\-]\s*\d{4})",
    r"hết\s+hiệu\s+lực\s+(?:thi\s+hành\s+)?(?:kể\s+từ\s+)?ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
    r"hết\s+hiệu\s+lực\s+vào\s+ngày\s+(\d{1,2}\s*[/\-]\s*\d{1,2}\s*[/\-]\s*\d{4})",
    r"hết\s+hiệu\s+lực\s+vào\s+ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
]
# Narrow patterns for enforcement context — thêm "đến hết ngày" (cần xác nhận enforcement)
_EXPIRY_NARROW_PATTERNS = _EXPIRY_STRICT_PATTERNS + [
    r"đến\s+hết\s+ngày\s+(\d{1,2}\s*[/\-]\s*\d{1,2}\s*[/\-]\s*\d{4})",
    r"đến\s+hết\s+ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
]
# Broad patterns — chỉ an toàn trong enforcement section (dễ false positive ở Điều khoản chuyển tiếp)
_EXPIRY_BROAD_PATTERNS = [
    r"đến\s+trước\s+ngày\s+(\d{1,2}\s*[/\-]\s*\d{1,2}\s*[/\-]\s*\d{4})",
    r"đến\s+trước\s+ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
    r"đến\s+ngày\s+(\d{1,2}\s*[/\-]\s*\d{1,2}\s*[/\-]\s*\d{4})",
    r"đến\s+ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
]


def _extract_expiry_from_section(section: str, enforcement_context: bool = False) -> Optional[str]:
    """Helper: quét section với expiry_patterns, trả về date đầu tiên match.

    Args:
        section: Nội dung cần quét.
        enforcement_context: True nếu section đã được xác định là enforcement (an toàn dùng cả broad patterns).
                            False nếu là full-content scan (chỉ dùng narrow patterns).
    """
    if not section:
        return None
    # Strip markdown links [text](url) → text để doc_number trong link hiện rõ
    section_lower = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', section.lower())

    expiry_patterns = list(_EXPIRY_STRICT_PATTERNS)
    if enforcement_context:
        expiry_patterns += _EXPIRY_NARROW_PATTERNS[len(_EXPIRY_STRICT_PATTERNS):]  # chỉ thêm "đến hết ngày"
        expiry_patterns += _EXPIRY_BROAD_PATTERNS

    # Phân tách section_lower thành các khoản (numbered paragraphs + Điều headings).
    # Mỗi khoản bắt đầu bằng "X. ", "X) " hoặc "Điều X.".
    # Nếu 1 khoản chứa cả "số X" (VB khác) và "hết hiệu lực ... ngày" → expiry của VB khác → skip.
    # Chỉ lấy expiry date từ khoản không có doc_number reference (là của VB hiện tại).
    lines = section_lower.split('\n')
    paragraphs = []
    current_para = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r'^(?:\d+|điều\s+\d+)\\?[\.\)]\s', line, re.IGNORECASE):
            if current_para.strip():
                paragraphs.append(current_para.strip())
            current_para = line + "\n"
        else:
            current_para += line + "\n"
    if current_para.strip():
        paragraphs.append(current_para.strip())

    # Nếu không tách được paragraph → fallback: dùng toàn bộ section
    if not paragraphs:
        paragraphs = [section_lower]

    doc_num_pat = r"số\s+" + _CONFIG_DOC_NUMBER_RE
    # Pattern: "Các [VB] sau đây hết hiệu lực" → toàn bộ paragraph là list VB khác
    _list_other_docs_pat = re.compile(
        r'(?:các|những)\s+(?:quy[ếe]t\s*đ[ịi]nh|v[ăa]n\s*b[ảa]n|ngh[ịi]\s*đ[ịi]nh|th[ôo]ng\s*t[ưu])\s+sau\s+đ[âa]y\s+h[ếe]t\s+hi[ệe]u\s+l[ựư]c',
        re.IGNORECASE
    )

    for para in paragraphs:
        # Fix 3: Skip toàn bộ paragraph nếu là list "Các VB sau đây hết hiệu lực"
        if _list_other_docs_pat.search(para):
            continue

        # Fix 4: Tìm TẤT CẢ vị trí "số X" trong paragraph (có thể có nhiều VB khác)
        other_doc_positions = [m.start() for m in re.finditer(doc_num_pat, para)] if re.search(doc_num_pat, para) else []

        for pat in expiry_patterns:
            for m in re.finditer(pat, para):
                # Fix 4: Skip nếu expiry match NẰM SAU bất kỳ số VB khác nào
                skip_this = False
                if other_doc_positions:
                    for other_pos in other_doc_positions:
                        if m.start() > other_pos and ("hết hiệu lực" in m.group(0) or "đến hết ngày" in m.group(0)):
                            skip_this = True
                            break
                if skip_this:
                    continue
                groups = m.groups()
                if len(groups) == 1:
                    candidate = groups[0].replace(" ", "")
                    parsed = parse_vietnamese_date(candidate)
                else:
                    candidate = f"ngày {groups[0]} tháng {groups[1]} năm {groups[2]}"
                    parsed = parse_vietnamese_date(candidate)
                if parsed:
                    return parsed
    return None


def extract_expiry_date_from_enforcement(enf_text: str) -> Optional[str]:
    """Trích xuất expiry_date CHỈ từ enforcement text (đã được xác định là
    điều/chương 'Hiệu lực thi hành' hoặc 'Tổ chức thực hiện').

    Dùng tất cả patterns (strict + narrow + broad) vì context đã được xác nhận
    là enforcement bởi chunking system (section_type='enforcement').

    Double-check: nếu enforcement text KHÔNG chứa keyword hiệu lực/hết hiệu lực
    → dùng strict patterns only (phòng trường hợp chunk bị phân loại nhầm).

    Không scan toàn bộ content → tránh false positive từ:
    - "Thời kỳ kiểm tra: ... đến hết ngày X"
    - Điều khoản chuyển tiếp: "thủ tục được áp dụng từ X đến hết ngày Y"
    - Cross-reference: "VB X hết hiệu lực từ ngày Y"

    Args:
        enf_text: Nội dung enforcement chunk(s) từ document_chunks.

    Returns:
        YYYY-MM-DD string hoặc None.
    """
    if not enf_text:
        return None

    # Verify enforcement context: text phải chứa keyword hiệu lực / hết hiệu lực
    enf_lower = enf_text.lower()
    has_enforcement_keywords = any(
        kw in enf_lower
        for kw in ("hiệu lực", "hết hiệu lực", "có hiệu lực", "thi hành")
    )
    is_enforcement = has_enforcement_keywords

    parsed = _extract_expiry_from_section(enf_text, enforcement_context=is_enforcement)
    if parsed:
        return parsed

    return None


def extract_expiry_date(content: str, enf_text: Optional[str] = None) -> Optional[str]:
    """Trích xuất expiry_date (YYYY-MM-DD).

    CHỈ trích xuất từ enforcement text (từ document_chunks section_type='enforcement').
    Nếu không có enf_text → dùng _find_effective_article để tìm enforcement article trong content.
    KHÔNG scan toàn bộ content — tránh false positive từ:
    - Điều khoản chuyển tiếp: "thủ tục được áp dụng đến hết ngày Y"
    - "Thời kỳ kiểm tra: ... đến hết ngày X"
    - Cross-reference: "VB số X hết hiệu lực từ ngày Y"

    Args:
        content: Toàn văn nội dung document (dùng làm fallback khi không có enf_text).
        enf_text: Nội dung enforcement chunk(s) — nguồn chính xác nhất.

    Returns:
        YYYY-MM-DD string hoặc None.
    """
    if enf_text:
        return extract_expiry_date_from_enforcement(enf_text)

    if not content:
        return None

    # Fallback: tìm enforcement article trong content
    section = _find_effective_article(content)
    if section:
        parsed = _extract_expiry_from_section(section, enforcement_context=True)
        if parsed:
            return parsed

    section = extract_effective_date_section(content)
    if section:
        parsed = _extract_expiry_from_section(section, enforcement_context=True)
        if parsed:
            return parsed

    return None


def validate_expiry_against_effective(
    expiry_date: Optional[str],
    effective_date: Optional[str],
) -> Optional[str]:
    """Validate: nếu expiry_date < effective_date → rõ ràng sai → trả về None.

    Phải có cả 2 giá trị mới check. Nếu 1 trong 2 thiếu → giữ nguyên expiry_date.
    """
    if not expiry_date or not effective_date:
        return expiry_date
    try:
        eff = effective_date.strip()
        exp = expiry_date.strip()
        if eff and exp and exp < eff:
            return None
    except Exception:
        pass
    return expiry_date


def extract_effective_date_from_enforcement(
    enf_text: str,
    issued_date: Optional[str] = None,
) -> Optional[str]:
    """Trích xuất effective_date từ enforcement article text.

    Không cần _find_effective_article vì enf_text đã là enforcement content.
    Chỉ quét các after_kw_patterns + signing pattern + delay pattern.

    Args:
        enf_text: Nội dung điều khoản thi hành (enforcement chunk).
        issued_date: Ngày ký/ban hành — fallback cho pattern "sau X ngày kể từ ngày ký".

    Returns:
        YYYY-MM-DD string hoặc None.
    """
    if not enf_text:
        return None

    after_kw_patterns = [
        r"có\s+hiệu\s+lực\s+thi\s+hành\s+kể\s+từ\s+ngày\s+([^.,;\n]+)",
        r"có\s+hiệu\s+lực\s+thi\s+hành\s+từ\s+ngày\s+([^.,;\n]+)",
        r"có\s+hiệu\s+lực\s+(?:thi\s+hành\s+)?(?:kể\s+từ\s+|từ\s+|vào\s+)?ngày\s+([^.,;\n]+)",
        r"hiệu\s+lực\s+thi\s+hành\s+(?:kể\s+từ\s+|từ\s+)?ngày\s+([^.,;\n]+)",
        r"thi\s+hành\s+(?:kể\s+từ\s+|từ\s+)?ngày\s+([^.,;\n]+)",
    ]

    # Nếu text dẫn chiếu VB khác → không parse date trực tiếp
    # (vì date bắt được sẽ là ngày ban hành của VB kia, không phải effective_date của VB này)
    if not find_cross_ref_doc_number(enf_text):
        parsed = _extract_date_from_text(enf_text, after_kw_patterns)
        if parsed:
            return parsed

    delay = _calc_effective_from_signing_delay(enf_text, issued_date)
    if delay:
        return delay

    return None


_ROMAN_TO_INT = {
    'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7,
    'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13,
    'xiv': 14, 'xv': 15, 'xvi': 16, 'xvii': 17, 'xviii': 18,
    'xix': 19, 'xx': 20, 'xxi': 21, 'xxii': 22, 'xxiii': 23, 'xxiv': 24,
}


def _parse_roman(s: str) -> Optional[int]:
    return _ROMAN_TO_INT.get(s.strip().lower())


def extract_chunk_effective_dates_from_enforcement(
    enf_text: str, main_effective_date: Optional[str] = None
) -> List[Dict]:
    """Extract per-provision effective dates from enforcement text.

    Parses clauses like:
        "Điều 7 và Phụ lục IV...có hiệu lực từ ngày 01 tháng 7 năm 2026"
        "Khoản 3 Điều 50...có hiệu lực từ ngày 01 tháng 01 năm 2026"

    Returns list of dicts:
        [{provision, article, clause, appendix, effective_date}, ...]
    """
    results: List[Dict] = []
    if not enf_text:
        return results

    # 1. Determine main date if not provided
    main_date = main_effective_date
    if not main_date:
        for m in re.finditer(
            r'(?:luật|nghị\s+định|thông\s+tư|quyết\s+định)\s+này\s+có\s+hiệu\s+lực\s+(?:thi\s+hành\s+)?(?:kể\s+)?từ\s+ngày\s+'
            r'(\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}|\d{2}/\d{2}/\d{4})',
            enf_text, re.IGNORECASE
        ):
            main_date = parse_vietnamese_date(m.group(0))
            break

    # 2. Find clauses with their own effective dates (not the main "Luật này" clause)
    # Pattern: specific provisions "có hiệu lực...từ ngày DATE"
    # NOTE: We match ONLY "có hiệu lực" patterns, NOT "hết hiệu lực" patterns.
    DATE_AFTER_EFFECTIVE = (
        r'(?<!hết\s)(?:có\s+hiệu\s+lực\s+(?:thi\s+hành\s+)?(?:kể\s+)?từ\s+ngày\s+)'
        r'(\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}|\d{2}/\d{2}/\d{4})'
    )

    # Split enforcement text into clause-level segments
    segments = re.split(r'\n(?=\d+\s*\.\s)', enf_text)
    if len(segments) <= 1:
        segments = [enf_text]

    seen = set()

    for segment in segments:
        segment_lower = segment.lower()

        # Skip segments that talk about EXPIRY (hết hiệu lực), not EFFECTIVE (có hiệu lực)
        # But allow segments that have BOTH "có hiệu lực" and "hết hiệu lực"
        # Rule: skip if the segment's primary date is tied to "hết hiệu lực"
        # (preceded by "hết hiệu lực" rather than "có hiệu lực")
        has_effective = bool(re.search(r'có\s+hiệu\s+lực', segment_lower))
        has_expiry_before_date = bool(re.search(r'hết\s+hiệu\s+lực.*từ\s+ngày\s+', segment_lower))

        if has_expiry_before_date and not has_effective:
            continue
        if has_expiry_before_date and has_effective:
            # Check which phrase appears right before the date
            date_positions = []
            for m in re.finditer(
                r'từ\s+ngày\s+(\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}|\d{2}/\d{2}/\d{4})',
                segment, re.IGNORECASE
            ):
                date_positions.append(m.start())
            if date_positions:
                # Find the phrase that precedes each date position
                for dp in date_positions:
                    context = segment[max(0, dp - 80):dp]
                    if re.search(r'hết\s+hiệu\s+lực', context, re.IGNORECASE):
                        if not re.search(r'có\s+hiệu\s+lực', context, re.IGNORECASE):
                            # This specific date context is about expiry
                            # If this is the ONLY date or the primary one, skip
                            continue

        # Find effective date in this segment
        date_match = re.search(DATE_AFTER_EFFECTIVE, segment, re.IGNORECASE)
        if not date_match:
            continue

        date_str = date_match.group(1)
        parsed_date = parse_vietnamese_date(date_str)
        if not parsed_date:
            continue

        # Skip if this is the main "Luật này" clause (same date as main)
        if main_date and parsed_date == main_date:
            if re.search(r'(?:luật|nghị\s+định|thông\s+tư|quyết\s+định)\s+này\s+có\s+hiệu\s+lực', segment_lower):
                continue

        # Skip "trừ trường hợp" reference lines (just pointers, no actual dates)
        if re.search(r'trừ\s+(?:trường\s+hợp\s+)?quy\s+định\s+tại', segment_lower):
            continue

        # Extract provisions from before "có hiệu lực"
        pre_eff = segment[:date_match.start()].strip()
        pre_eff = re.sub(r'^\d+\s*\.\s*', '', pre_eff).strip()

        articles = []
        clause_entries = []  # [{clause, article}]
        appendixes = []
        clause_articles = set()  # Articles that have clause-specific refs

        # Extract "Khoản X Điều Y" / "các khoản X, Y và Z Điều A"
        for m in re.finditer(
            r'(?:[Cc]ác\s+)?[Kk]hoản\s+(\d+[a-zđ]?(?:\s*(?:[,;]|và)\s*\d+[a-zđ]?)*)\s+[Đđ]iều\s+(\d+)',
            pre_eff
        ):
            a_num = m.group(2).strip()
            c_nums = re.findall(r'\d+[a-zđ]?', m.group(1))
            for c_num in c_nums:
                entry = {"clause": c_num, "article": a_num}
                if entry not in clause_entries:
                    clause_entries.append(entry)
                clause_articles.add(a_num)

        # Extract standalone "Khoản X" / "các khoản X, Y và Z" (no explicit Điều)
        if not clause_entries:
            for m in re.finditer(
                r'(?:[Cc]ác\s+)?[Kk]hoản\s+(\d+[a-zđ]?(?:\s*(?:[,;]|và)\s*\d+[a-zđ]?)*)',
                pre_eff
            ):
                nums = re.findall(r'\d+[a-zđ]?', m.group(1))
                for n in nums:
                    if n and n.isdigit():
                        clause_entries.append({"clause": n, "article": None})

        # Extract "Điều X" / "Các điều X, Y, Z" references
        for m in re.finditer(
            r'(?:[Cc]ác\s+)?[Đđ]iều\s+(\d+[a-zđ]?(?:\s*(?:[,;]|và)\s*\d+[a-zđ]?)*)',
            pre_eff
        ):
            nums = re.findall(r'\d+[a-zđ]?', m.group(1))
            for a in nums:
                a = a.strip()
                if a and a.isdigit() and a not in clause_articles:
                    articles.append(a)

        # Extract "Phụ lục X" references (also "Danh mục...tại Phụ lục X")
        for m in re.finditer(r'[Pp]hụ\s+[Ll]ục\s+([IVXLCDM\d]+)', pre_eff):
            pl = m.group(1).strip()
            roman_val = _parse_roman(pl)
            if roman_val:
                appendixes.append(str(roman_val))
            else:
                appendixes.append(pl)

        # Build result entries
        provision_text = pre_eff[:200].strip().rstrip(',;').strip()

        for a in articles:
            key = ("article", int(a), None, None, parsed_date)
            if key not in seen:
                seen.add(key)
                results.append({
                    "provision": provision_text,
                    "article": int(a),
                    "clause": None,
                    "appendix": None,
                    "effective_date": parsed_date,
                })

        for c in clause_entries:
            c_article = c.get("article")
            c_clause = int(c["clause"]) if c["clause"].isdigit() else c["clause"]
            art_val = int(c_article) if c_article and c_article.isdigit() else None
            key = ("clause", art_val, c_clause, None, parsed_date)
            if key not in seen:
                seen.add(key)
                results.append({
                    "provision": provision_text,
                    "article": art_val,
                    "clause": c_clause,
                    "appendix": None,
                    "effective_date": parsed_date,
                })

        for pl in appendixes:
            key = ("appendix", None, None, pl, parsed_date)
            if key not in seen:
                seen.add(key)
                results.append({
                    "provision": provision_text,
                    "article": None,
                    "clause": None,
                    "appendix": pl,
                    "effective_date": parsed_date,
                })

        if not articles and not clause_entries and not appendixes:
            results.append({
                "provision": provision_text,
                "article": None,
                "clause": None,
                "appendix": None,
                "effective_date": parsed_date,
            })

    return results


def extract_expiry_relations_from_enforcement(enf_text: str, title: str = "") -> List[Dict]:
    """Trích xuất quan hệ hết hiệu lực từ enforcement article text.

    Bao gồm:
    - VB cũ hết hiệu lực kể từ ngày VB mới có hiệu lực
    - Bãi bỏ/thay thế/sửa đổi các VB khác
    - Doc numbers trong sub-bullets (a), (b), –, • sau "sau đây hết hiệu lực"

    Args:
        enf_text: Nội dung điều khoản thi hành.
        title: Tiêu đề văn bản (để hỗ trợ trích xuất).

    Returns:
        List[Dict] — same format as extract_relations().
    """
    if not enf_text:
        return []
    # Strip markdown links [text](url) → text trước khi xử lý
    enf_clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', enf_text)
    result = extract_relations(enf_clean, title)

    existing = {r["doc_number"].lower() for r in result}

    # Pattern cho Luật-type: "Luật X số Y ... hết hiệu lực kể từ ngày Luật này có hiệu lực thi hành"
    # trong đó doc_number X có thể cách "hết hiệu lực" bởi rất nhiều text sửa đổi
    for m in re.finditer(
        r'(?:Luật|Nghị\s+định|Thông\s+tư|Quyết\s+định)\s+[\w\s]*?số\s+(' + _DOC_NUMBER_RE + r')'
        r'.*?hết\s+hiệu\s+lực\s+kể\s+từ\s+ngày\s+(?:Luật|Nghị\s+định|Thông\s+tư|Quyết\s+định)\s+này\s+có\s+hiệu\s+lực',
        enf_clean, re.IGNORECASE
    ):
        d = m.group(1).strip().rstrip("-/")
        if d and len(d) >= 5 and d.lower() not in existing:
            existing.add(d.lower())
            result.append({
                "doc_number": d,
                "relation_type": "abolishes",
            })

    # Sub-bullet scan: các doc number trong dòng bullet (a), (b), –, • sau "hết hiệu lực"
    if re.search(r'(?:hết\s+hiệu\s+lực|bãi\s+bỏ)', enf_clean, re.IGNORECASE):
        for m in re.finditer(
            r'(?:^[a-zđ]\)\s*|^–\s*|^•\s*|^\d+\.\s*)'
            r'(?:[\wĐđ]+\s+){0,3}(?:số\s+)?(' + _DOC_NUMBER_RE + r')',
            enf_clean, re.MULTILINE | re.IGNORECASE
        ):
            d = m.group(1).strip().rstrip("-/")
            if d and len(d) >= 5 and d.lower() not in existing:
                existing.add(d.lower())
                result.append({
                    "doc_number": d,
                    "relation_type": "abolishes",
                })

    # Fallback chung: nếu enforcement có "hết hiệu lực/bãi bỏ/thay thế"
    # nhưng không tìm ra số hiệu cụ thể → điền '0' để tránh lỗi crawl
    if not result:
        if re.search(r'(?:hết\s+hiệu\s+lực|bãi\s+bỏ|thay\s+thế)', enf_clean, re.IGNORECASE):
            result.append({
                "doc_number": "0",
                "relation_type": "abolishes",
            })

    return result


def _normalize_to_iso(date_str: Optional[str]) -> Optional[str]:
    """Convert dd/mm/yyyy hoặc yyyy-mm-dd → yyyy-mm-dd."""
    if not date_str:
        return None
    date_str = date_str.strip()
    # Already ISO
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    # dd/mm/yyyy
    m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", date_str)
    if m:
        d, mo, y = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    # Try parse as Vietnamese date
    return parse_vietnamese_date(date_str)


# ── Public API ────────────────────────────────────────────────────────────


def extract_keywords(
    title: str,
    content: str,
    doc_number: Optional[str] = None,
    max_keywords: int = 10,
) -> List[str]:
    """Trích keywords từ title + content bằng rule-based.

    Chiến lược:
    1. Luôn thêm số hiệu văn bản nếu có
    2. Tách title → chọn từ có nghĩa (dài >= 3 ký tự, không stopword)
    3. Tách content → chọn danh từ riêng, số hiệu, năm
    4. Lọc, dedup, trả về tối đa max_keywords
    """
    keywords: List[str] = []
    seen: set = set()

    def add(word: str):
        word = word.strip()
        if not word or len(word) < 2:
            return
        key = word.lower()
        if key in seen:
            return
        seen.add(key)
        if re.match(r"^[\d/]+$", word) or re.match(r"^[A-ZĐ]{2,}(-[A-ZĐ]{2,})*$", word):
            keywords.append(word)
        else:
            keywords.append(word.title())

    if doc_number:
        add(doc_number)

    title_clean = re.sub(r"[\ufeff\u200b]", "", title)
    for token in _tokenize(title_clean):
        t = token.lower()
        if t not in STOPWORDS and len(t) >= 3:
            add(token)

    if content:
        for m in re.finditer(
            r"(Điều|Khoản|Chương|Mục|Phần)\s+[\dIVXLCH]+\b",
            content[:5000],
        ):
            add(m.group(0))

        for m in re.finditer(r"\b[A-ZĐ]{2,}(?:-[A-ZĐ]{2,})*\b", content[:2000]):
            if 2 <= len(m.group(0)) <= 10:
                add(m.group(0))

        for m in re.finditer(r"\b(19|20)\d{2}\b", content[:2000]):
            add(m.group(0))

    result = []
    for k in keywords:
        if len(k) >= 3 or re.match(r"[\d/]", k):
            result.append(k)

    return result[:max_keywords]


def detect_category(title: str = "") -> str:
    """Phát hiện chuyên mục pháp luật từ title.

    Trả về tên tiếng Việt viết hoa chữ đầu: 'Hình sự', 'Hành chính', ... hoặc 'Khác'."""
    result = None

    if title:
        title_lower = title.lower()
        for pattern, cat_name in TITLE_KEYWORDS_MAP:
            if re.search(pattern, title_lower):
                result = cat_name
                break

    if not result:
        result = "khác"

    # Capitalize chữ đầu: "hành chính" → "Hành chính", "lao động - tiền lương" → "Lao động - Tiền lương"
    words = result.split(" - ")
    words = [w[0].upper() + w[1:] if w else "" for w in words]
    return " - ".join(words) if result else "Khác"


def extract_query_keywords(query: str) -> List[str]:
    """Trích keywords từ câu query tìm kiếm (cho crawl_by_query).

    Giữ: số hiệu (168/2024/NĐ-CP), năm, danh từ riêng.
    Bỏ: stopwords.
    """
    keywords: List[str] = []
    seen: set = set()

    def add(word: str):
        w = word.strip()
        if not w or w.lower() in seen:
            return
        seen.add(w.lower())
        if re.match(r"^[\d/]+$", w) or re.match(r"^[A-ZĐ]{2,}(-[A-ZĐ]{2,})*$", w):
            keywords.append(w)
        else:
            keywords.append(w.capitalize())

    for m in re.finditer(r"\d+[\s/]*[–\-]?[\s/]*\d{4}[\s/]*[–\-]?[\s/]*[A-ZĐ]+", query):
        add(m.group(0))

    for token in _tokenize(query):
        t = token.lower()
        if t not in STOPWORDS and len(t) >= 3:
            add(token)

    for m in re.finditer(r"\b(19|20)\d{2}\b", query):
        add(m.group(0))

    return keywords[:8]


def extract_metadata(
    title: str,
    content: str,
    url: str = "",
    hint_category: Optional[str] = None,
    doc_id: str = "",
    issued_date: Optional[str] = None,
    effective_date: Optional[str] = None,
) -> Dict:
    """Rule-based metadata extraction — nhanh, local, không tốn API.

    Output: {"category": "...", "effective_date": "YYYY-MM-DD" or None, "expiry_date": "YYYY-MM-DD" or None}
    """
    eff = extract_effective_date(content, issued_date=issued_date)
    if not eff and effective_date:
        eff = effective_date
    expiry = extract_expiry_date(content)
    if expiry and eff:
        expiry = validate_expiry_against_effective(expiry, eff)
    return {
        "category": detect_category(title=title),
        "effective_date": eff,
        "expiry_date": expiry,
    }


def extract_relations(content: str, title: str = "") -> List[Dict]:
    """Trích xuất quan hệ thay thế/bãi bỏ/sửa đổi từ content.

    Returns:
        List[Dict] — [
            {"doc_number": "...", "relation_type": "abolishes"},
            {"doc_number": "...", "relation_type": "amends_partial"},
        ]
    """
    if not content:
        return []

    results: List[Dict] = []
    seen: set = set()

    def _extract_context(content: str, match_end: int) -> dict:
        """Extract context xung quanh vị trí match: old_issued_date, authority_hint, title_hint."""
        ctx_start = max(0, match_end - 50)
        ctx_end = min(len(content), match_end + 500)
        ctx = content[ctx_start:ctx_end]

        ctx_result = {}

        # Extract date "ngày X tháng Y năm Z" hoặc "ngày dd/mm/yyyy" gần match → old_issued_date
        date_m = re.search(
            r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
            ctx, re.IGNORECASE
        )
        if not date_m:
            date_m = re.search(
                r'ngày\s+(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
                ctx, re.IGNORECASE
            )
        if date_m:
            d, m, y = int(date_m.group(1)), int(date_m.group(2)), int(date_m.group(3))
            if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2099:
                ctx_result["old_issued_date"] = f"{y:04d}-{m:02d}-{d:02d}"

        # Title hint: text giữa "của [Authority]" và dấu chấm cuối câu
        auth_m = re.search(
            r'của\s+([^,;.\n]+?)\s+'
            r'(?:ban\s+hành\s+|phê\s+duyệt\s+|quy\s+định\s+|về\s+)?(.*?)(?:[\.]\s*$|[\.]\s+[A-ZĐ])',
            ctx, re.IGNORECASE | re.DOTALL
        )
        if auth_m:
            ctx_result["issuing_authority_hint"] = auth_m.group(1).strip().rstrip(".,; ")
            title_part = auth_m.group(2).strip().rstrip(".,; ")
            if title_part and len(title_part) > 10:
                ctx_result["title_hint"] = title_part[:300]

        return ctx_result

    def _get_authority(match, group_idx: int) -> Optional[str]:
        try:
            val = match.group(group_idx)
            if val:
                return val.strip().rstrip(".,;")
        except IndexError:
            pass
        return None

    # 1. Partial amend patterns (ưu tiên trước — cụ thể hơn)
    for pattern, rel_type in PARTIAL_AMEND_PATTERNS:
        for m in re.finditer(pattern, content):
            provision_text = m.group(1).strip()
            doc_num = m.group(2).strip().rstrip("-/")
            if not doc_num or len(doc_num) < 5:
                continue
            # Nếu đã có relation toàn bộ cho doc này → không thêm partial
            key = (doc_num.lower(), rel_type, provision_text.lower()[:50])
            if key in seen:
                continue
            seen.add(key)
            ctx = _extract_context(content, m.end())
            results.append({
                "doc_number": doc_num,
                "relation_type": rel_type,
                "issuing_authority_hint": _get_authority(m, 3) or ctx.get("issuing_authority_hint"),
                "old_issued_date": ctx.get("old_issued_date"),
                "title_hint": ctx.get("title_hint"),
            })

    # 2. Whole-document patterns (group(1)=doc_number, group(2)=authority)
    for pattern, rel_type in RELATION_PATTERNS:
        for m in re.finditer(pattern, content):
            doc_num = m.group(1).strip().rstrip("-/")
            if not doc_num or len(doc_num) < 5:
                continue
            key_base = doc_num.lower()
            # Nếu đã có partial cho doc này + rel là amends → skip (partial đã đủ)
            already_partial = any(
                r["doc_number"].lower() == key_base and r["relation_type"] == "amends_partial"
                for r in results
            )
            if already_partial and rel_type == "amends":
                continue
            key = (key_base, rel_type)
            if key in seen:
                continue
            seen.add(key)
            ctx = _extract_context(content, m.end())
            results.append({
                "doc_number": doc_num,
                "relation_type": rel_type,
                "issuing_authority_hint": _get_authority(m, 2) or ctx.get("issuing_authority_hint"),
                "old_issued_date": ctx.get("old_issued_date"),
                "title_hint": ctx.get("title_hint"),
            })

    # ── 3. Bullet-point scan: sau "thay thế:" hoặc "bãi bỏ:" + dòng bullet ──
    for m in re.finditer(
        r'(?:[Tt]hay\s+thế|[Bb]ãi\s+bỏ|[Hh]ết\s+hiệu\s+lực)\s*:\s*\n'
        r'((?:\s*[-–•]\s*.*?\n)+)',
        content, re.MULTILINE
    ):
        bullet_block = m.group(1)
        rel_type = "replaces" if "thay thế" in m.group(0).lower() else "abolishes"
        for bm in re.finditer(
            r'(?:số\s+)?(' + _DOC_NUMBER_RE + r')\s+ngày\s+(\d{1,2}\D+\d{1,2}\D+\d{4})',
            bullet_block, re.IGNORECASE
        ):
            dn = bm.group(1).strip().rstrip("-/")
            if not dn or len(dn) < 5:
                continue
            key = (dn.lower(), rel_type)
            if key in seen:
                continue
            seen.add(key)
            date_str = bm.group(2)
            old_date = _normalize_to_iso(date_str) or parse_vietnamese_date(f"ngày {date_str}")
            results.append({
                "doc_number": dn,
                "relation_type": rel_type,
                "issuing_authority_hint": None,
                "old_issued_date": old_date,
                "title_hint": None,
            })

    return results


# ── Internal helpers ──────────────────────────────────────────────────────


def _tokenize(text: str) -> List[str]:
    """Tách từ đơn giản bằng regex, không cần thư viện NLP.

    Giữ các cụm ghép bằng dấu gạch: 'an-ninh-mang', 'ND-CP'
    """
    tokens = re.findall(r"[\wĐđ]+(?:[-][\wĐđ]+)*", text.lower())
    return tokens
