"""
Loại bỏ rác từ web scraping ra khỏi content văn bản pháp luật.
"""
import re
import unicodedata

CONTENT_CLEAN_ORDER = [
    # 1. Footer nav block: từ dòng "* Lưu trữ" đến cuối
    (r'\n\s*\*\s*Lưu trữ.*', ''),

    # 2. Quảng cáo dạng image markdown
    (r'\[!\[.*?\]\(.*?thuvienphapluat.*?\)\]\(.*?\)', ''),

    # 3. "Bài liên quan" và links bài viết
    (r'\n\s*\*\s*Bài liên quan:.*?(?=\n\s*\*)', ''),
    (r'\n\s*\*\s*\[?!\[.*?\]\(.*?\).*?\]?\(.*?\)', ''),
]


def clean_content(content: str) -> str:
    """Remove web-scraping garbage from legal document content."""
    if not content:
        return content

    result = content

    # Strategy: find the first occurrence of footer garbage markers
    markers = [
        '* Lưu trữ',
        '* **Ghi chú**',
        '* Ý kiến',
        '* [Facebook ',
        '* Email',
        '* In',
        '* [ Hỏi đáp pháp luật',
        '* [ Pháp Luật Thuế',
        '* [ Bản án liên quan',
        '* [PHÁP LUẬT DOANH NGHIỆP',
    ]

    lines = result.split('\n')
    cut_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        for marker in markers:
            if stripped.startswith(marker) or stripped == marker:
                cut_idx = i
                break
        if cut_idx is not None:
            break

    if cut_idx is not None:
        lines = lines[:cut_idx]
        result = '\n'.join(lines)

    # Remove trailing English title duplicates (Circular/Decree/Ordinance... No.)
    lines = result.rsplit('\n', 1)
    if len(lines) == 2:
        first, last = lines
        if re.match(r'^\s*(Circular|Decree|Ordinance|Resolution)\s+No\.', last, re.IGNORECASE):
            result = first.rstrip('\n')
    elif len(lines) == 1:
        if re.match(r'^\s*(Circular|Decree|Ordinance|Resolution)\s+No\.', lines[0], re.IGNORECASE):
            result = ''

    return result.strip()


def has_garbage(content: str) -> bool:
    """Check if content contains known garbage patterns."""
    markers = [
        '* Lưu trữ',
        '* **Ghi chú**',
        '* Ý kiến',
        '* [Facebook ',
        '* Email',
        '* In',
        '* [ Hỏi đáp pháp luật',
        '* [ Pháp Luật Thuế',
        '* [ Bản án liên quan',
        '* [PHÁP LUẬT DOANH NGHIỆP',
    ]
    for m in markers:
        if m in content:
            return True
    return False
