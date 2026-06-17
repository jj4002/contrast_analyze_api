"""
Topic-aware legal retrieval cho hợp đồng lao động.
Keyword-based topic detection → targeted FAISS search queries.
Không dùng LLM — thuần keyword matching.
"""
import re
from typing import Dict, List
from services.vectorstore.document import Document
from services.vectorstore.faiss_store import get_legal_collection
from config import TOP_K_RETRIEVAL, SIMILARITY_THRESHOLD

# ── Labor contract topics ────────────────────────────────────────────────
# Mỗi topic có: keywords (để detect từ contract text), search_queries (để search FAISS)

LABOR_TOPICS: Dict[str, dict] = {
    "salary": {
        "keywords": ["lương", "mức lương", "tiền lương", "thu nhập", "trả lương",
                     "phụ cấp", "thưởng", "nâng lương", "lương cơ bản", "lương tháng",
                     "luong", "muc luong", "tien luong", "thu nhap", "phu cap"],
        "search_queries": [
            "mức lương tối thiểu vùng",
            "tiền lương cơ bản người lao động",
            "phụ cấp lương trợ cấp",
            "hình thức trả lương thời hạn trả lương",
            "nâng lương thưởng chế độ đãi ngộ",
        ],
    },
    "working_time": {
        "keywords": ["giờ làm", "thời gian làm", "nghỉ trưa", "ca làm", "giờ làm việc",
                     "thời giờ làm việc", "nghỉ ngơi", "nghỉ giải lao",
                     "gio lam", "thoi gian lam", "nghi trua", "thoi gio lam viec"],
        "search_queries": [
            "thời giờ làm việc thời giờ nghỉ ngơi",
            "giờ làm việc bình thường tối đa",
            "nghỉ giữa giờ nghỉ giải lao",
        ],
    },
    "overtime": {
        "keywords": ["tăng ca", "làm thêm", "thêm giờ", "ngoài giờ", "làm thêm giờ",
                     "overtime", "giờ làm thêm", "tang ca", "lam them gio"],
        "search_queries": [
            "làm thêm giờ tiền lương làm thêm giờ",
            "giới hạn số giờ làm thêm tối đa",
            "làm thêm giờ trong trường hợp đặc biệt",
        ],
    },
    "insurance": {
        "keywords": ["bảo hiểm", "bhxh", "bhyt", "bhtn", "bảo hiểm xã hội",
                     "bảo hiểm y tế", "bảo hiểm thất nghiệp", "bảo hiểm tai nạn",
                     "bao hiem", "bao hiem xa hoi", "bao hiem y te"],
        "search_queries": [
            "bảo hiểm xã hội bắt buộc mức đóng bảo hiểm xã hội",
            "bảo hiểm y tế bảo hiểm thất nghiệp",
            "trách nhiệm đóng bảo hiểm của người sử dụng lao động",
        ],
    },
    "leave": {
        "keywords": ["nghỉ phép", "nghỉ lễ", "nghỉ ốm", "thai sản", "nghỉ việc riêng",
                     "phép năm", "nghỉ không lương", "nghỉ chế độ",
                     "nghi phep", "nghi le", "nghi om", "thai san", "phep nam"],
        "search_queries": [
            "nghỉ phép năm ngày nghỉ lễ tết",
            "chế độ thai sản cho lao động nữ",
            "nghỉ ốm đau nghỉ việc riêng hưởng lương",
        ],
    },
    "termination": {
        "keywords": ["nghỉ việc", "thôi việc", "sa thải", "chấm dứt", "đơn phương",
                     "thanh lý hợp đồng", "thôi việc", "cho thôi việc",
                     "nghi viec", "thoi viec", "sa thai", "cham dut", "don phuong"],
        "search_queries": [
            "chấm dứt hợp đồng lao động đơn phương chấm dứt",
            "trợ cấp thôi việc trợ cấp mất việc làm",
            "nghĩa vụ của người lao động khi đơn phương chấm dứt",
        ],
    },
    "probation": {
        "keywords": ["thử việc", "tập sự", "học việc", "thời gian thử", "thử việc",
                     "thu viec", "tap su", "hoc viec"],
        "search_queries": [
            "thời gian thử việc tối đa theo luật",
            "tiền lương thử việc tỷ lệ phần trăm",
            "hợp đồng thử việc quyền và nghĩa vụ",
        ],
    },
    "discipline": {
        "keywords": ["kỷ luật", "cảnh cáo", "khiển trách", "phạt", "vi phạm nội quy",
                     "xử lý kỷ luật", "kỷ luật lao động", "trách nhiệm vật chất",
                     "ky luat", "canh cao", "khien trach", "xu ly ky luat"],
        "search_queries": [
            "kỷ luật lao động hình thức kỷ luật",
            "trách nhiệm vật chất bồi thường thiệt hại",
            "xử lý kỷ luật sa thải người lao động",
        ],
    },
    "benefits": {
        "keywords": ["phúc lợi", "trợ cấp", "ăn trưa", "xăng xe", "điện thoại",
                     "công tác phí", "đào tạo", "bồi dưỡng", "độc hại",
                     "phuc loi", "tro cap", "an trua", "xang xe", "dao tao"],
        "search_queries": [
            "phúc lợi người lao động trợ cấp",
            "chế độ bồi dưỡng độc hại nguy hiểm",
            "đào tạo bồi dưỡng nâng cao trình độ",
        ],
    },
    "tax": {
        "keywords": ["thuế", "thuế thu nhập", "tncn", "khấu trừ", "giảm trừ gia cảnh",
                     "thuế thu nhập cá nhân", "quyết toán thuế",
                     "thue", "thue thu nhap", "khau tru", "giam tru gia canh"],
        "search_queries": [
            "thuế thu nhập cá nhân đối với tiền lương tiền công",
            "khấu trừ thuế thu nhập cá nhân",
            "giảm trừ gia cảnh người phụ thuộc",
        ],
    },
}

# ── Topic detection ─────────────────────────────────────────────────────

def detect_topics(text: str) -> List[str]:
    """Detect which labor topics appear in contract text via keyword matching.

    Returns list of topic keys from LABOR_TOPICS (no duplicates).
    """
    text_lower = text.lower()
    found = []
    for topic, config in LABOR_TOPICS.items():
        for kw in config["keywords"]:
            if kw in text_lower:
                found.append(topic)
                break
    return found


def detect_topics_from_clauses(clauses_text: str) -> Dict[str, str]:
    """For a clause text, detect which topic it belongs to.

    Returns {topic_key: matched_keyword} for the best matching topic,
    or {"general": ""} if no match.
    """
    text_lower = clauses_text.lower()
    for topic, config in LABOR_TOPICS.items():
        for kw in config["keywords"]:
            if kw in text_lower:
                return {topic: kw}
    return {"general": ""}


# ── Topic-aware FAISS search ────────────────────────────────────────────

def retrieve_law_for_topic(topic: str, k: int = None) -> List[Document]:
    """Retrieve legal chunks for a specific labor topic using targeted queries.

    Searches FAISS legal collection with each topic-specific search query
    and merges results (deduplicated).
    """
    k = k or TOP_K_RETRIEVAL
    config = LABOR_TOPICS.get(topic)
    if not config:
        return []

    queries = config["search_queries"]
    collection = get_legal_collection()
    all_docs: List[Document] = []
    seen_texts = set()

    for q in queries:
        docs = collection.similarity_search(
            q, k=k, min_score=SIMILARITY_THRESHOLD
        )
        for d in docs:
            # Deduplicate by content hash
            text_hash = hash(d.page_content[:200])
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                all_docs.append(d)

    # FAISS returns results in similarity order, merge may shuffle but it's fine
    return all_docs[:k * 2]


def retrieve_law_for_topics(topics: List[str], k: int = None) -> Dict[str, List[Document]]:
    """Retrieve legal chunks for multiple topics.

    Returns {topic: [Document, ...]} dict.
    """
    result = {}
    for topic in topics:
        docs = retrieve_law_for_topic(topic, k=k)
        if docs:
            result[topic] = docs
    return result


def format_legal_context_with_status(docs: List[Document]) -> str:
    """Format legal chunks into context string with amendment/status metadata.

    Each chunk includes: doc_number, title, effective_date, status_flag,
    and any amendment info if available in metadata.
    """
    if not docs:
        return "Không có dữ liệu pháp luật liên quan."

    lines = []
    seen_docs = {}

    for d in docs:
        meta = d.metadata
        doc_number = meta.get("doc_number", "")
        title = meta.get("title", "")
        status_flag = meta.get("status_flag")
        effective_date = meta.get("effective_date", "")
        expiry_date = meta.get("expiry_date", "")
        section_type = meta.get("section_type", "")

        # Status label
        status_labels = {0: "Chưa xác định", 1: "Còn hiệu lực", 2: "Hết hiệu lực",
                         3: "Sắp có hiệu lực", 4: "Hết hiệu lực một phần", 5: "Có hiệu lực một phần"}
        status_text = status_labels.get(status_flag, "Không rõ")

        # Doc header (only once per doc)
        doc_key = (doc_number, effective_date)
        if doc_key not in seen_docs:
            header = f"\n--- {doc_number} - {title} ---"
            header += f"\n    Status: {status_text} (flag={status_flag})"
            if effective_date:
                header += f" | Hiệu lực từ: {effective_date}"
            if expiry_date:
                header += f" | Hết hiệu lực: {expiry_date}"
            seen_docs[doc_key] = header

        lines.append(seen_docs[doc_key])
        lines.append(d.page_content[:3000])

    return "\n".join(lines)


def format_clause_with_topic(clause: dict) -> str:
    """Format a contract clause for the analyze prompt."""
    clause_num = clause.get("clause_number", "")
    text = clause.get("text", "")
    return f"Điều khoản {clause_num}:\n{text}"
