"""
Extract amendment clauses from amending legal documents.
Detects: sửa đổi, bổ sung, bãi bỏ, thay thế cụm từ ở mức điều/khoản/điểm.
Also detects partial abolishment and replaced phrases.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AmendmentTarget:
    article: Optional[int] = None
    clause: Optional[str] = None
    point: Optional[str] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    special: Optional[str] = None


@dataclass
class ExtractedAmendment:
    action: str
    target_doc_number: Optional[str] = None
    targets: List[AmendmentTarget] = field(default_factory=list)
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    description: str = ""
    content: str = ""
    line_start: int = 0
    line_end: int = 0


_CN = r'(\d+[a-zđ]*)'
_PN = r'([a-zđ])'
_AN = r'(\d+)'

R_DOC_NUMBER = re.compile(
    r'(?:Luật|Nghị\s*định|Thông\s*tư|Pháp\s*lệnh)\s+(?:số\s+)?(\d+/\d+/[A-ZĐ]+(?:\d+)?(?:-[A-ZĐ]+(?:\d+)?)*)',
    re.IGNORECASE,
)

R_AMEND_CLAUSES = re.compile(
    r'Sửa\s*đổi,\s*bổ\s*sung\s+khoản\s+' + _CN +
    r'(?:\s+và\s+khoản\s+' + _CN + r')?'
    r'(?:\s*,\s*khoản\s+' + _CN + r')*'
    r'\s+(?:của\s+)?Điều\s+' + _AN,
    re.IGNORECASE,
)

R_AMEND_ARTICLE = re.compile(
    r'Sửa\s*đổi,\s*bổ\s*sung\s+Điều\s+(\d+)',
    re.IGNORECASE,
)

R_AMEND_POINT = re.compile(
    r'Sửa\s*đổi,\s*bổ\s*sung\s+điểm\s+' + _PN +
    r'\s+khoản\s+' + _CN +
    r'\s+(?:của\s+)?Điều\s+' + _AN,
    re.IGNORECASE,
)

R_AMEND_MULTI = re.compile(
    r'Sửa\s*đổi,\s*bổ\s*sung\s+một\s+số\s+khoản\s+(?:của\s+)?Điều\s+' + _AN,
    re.IGNORECASE,
)

R_AMEND_FIRST_PARA = re.compile(
    r'Sửa\s*đổi,\s*bổ\s*sung\s+đoạn\s+đầu\s+(?:của\s+)?khoản\s+' + _CN +
    r'\s+(?:của\s+)?Điều\s+' + _AN,
    re.IGNORECASE,
)

R_SUPPLEMENT_CLAUSE = re.compile(
    r'Bổ\s*sung\s+khoản\s+' + _CN +
    r'\s+vào\s+sau\s+khoản\s+' + _CN +
    r'\s+(?:của\s+)?Điều\s+' + _AN,
    re.IGNORECASE,
)

R_REPLACE_CLAUSE = re.compile(
    r'Thay\s+thế\s+cụm\s+từ\s*"(.+?)"\s*bằng\s*(?:cụm\s+từ\s*)?\s*"(.+?)"\s+'
    r'tại\s+khoản\s+' + _CN + r'\s+(?:của\s+)?Điều\s+' + _AN,
    re.IGNORECASE | re.DOTALL,
)

R_REPLACE_POINT = re.compile(
    r'Thay\s+thế\s+cụm\s+từ\s*"(.+?)"\s*bằng\s*(?:cụm\s+từ\s*)?\s*"(.+?)"\s+'
    r'tại\s+điểm\s+' + _PN + r'\s+khoản\s+' + _CN + r'\s+(?:của\s+)?Điều\s+' + _AN,
    re.IGNORECASE | re.DOTALL,
)

R_ABOLISH_CLAUSE = re.compile(
    r'Bãi\s*bỏ\s+khoản\s+' + _CN + r'\s+(?:của\s+)?Điều\s+' + _AN,
    re.IGNORECASE,
)

R_ABOLISH_ARTICLE = re.compile(
    r'Bãi\s*bỏ\s+Điều\s+(\d+)',
    re.IGNORECASE,
)

R_PARTIAL_ABOLISH = re.compile(
    r'(?:Luật|Nghị\s*định)\s+(?:số\s+)?(\d+/\d+/[A-ZĐ]+(?:\d+)?(?:-[A-ZĐ]+(?:\d+)?)*)'
    r'[^;.]*?(?:hết\s+hiệu\s+lực|hết\s+hiệu\s+lực\s+thi\s+hành)'
    r'[^;.]*?trừ\s+(.+?)(?:[.;]\s*$|[.;]\s)',
    re.IGNORECASE | re.DOTALL,
)

R_CHAPTER_TITLE = re.compile(
    r'Sửa\s*đổi,\s*bổ\s*sung\s+tên\s+Mục\s+(\d+)\s+Chương\s+([IVXL\d]+)',
    re.IGNORECASE,
)

R_SUB_AMEND = re.compile(
    r'[a-zđ]\)\s*Sửa\s*đổi,\s*bổ\s*sung\s+khoản\s+' + _CN,
    re.IGNORECASE,
)

R_AMEND_APPENDIX = re.compile(
    r'(?:Sửa\s*đổi,\s*bổ\s*sung|Bổ\s*sung,\s*bãi\s*bỏ|Bổ\s*sung,\s*sửa\s*đổi)\s+'
    r'(?:một\s+số\s+số\s+thứ\s+tự\s+(?:của\s+)?)?'
    r'Phụ\s+lục\s+([IVXL\d]+|[A-Z]+)',
    re.IGNORECASE,
)

R_AMEND_APPENDIX_ROW = re.compile(
    r'(?:Sửa\s*đổi,\s*bổ\s*sung|Bổ\s*sung|Bãi\s*bỏ|Sửa\s*đổi)\s+'
    r'số\s+thứ\s+tự\s+(\d+)(?:\s+và\s+số\s+thứ\s+tự\s+(\d+))?'
    r'(?:\s+vào\s+sau\s+số\s+thứ\s+tự\s+(\d+))?',
    re.IGNORECASE,
)

R_ABOLISH_APPENDIX_ROW = re.compile(
    r'Bãi\s*bỏ\s+(?:ngành,\s*nghề\s+)?[^.]+tại\s+số\s+thứ\s+tự\s+(\d+)',
    re.IGNORECASE,
)

R_REPLACE_APPENDIX = re.compile(
    r'Thay\s+thế\s+Phụ\s+lục\s+([IVXL\d]+|[A-Z]+)',
    re.IGNORECASE,
)

R_ABOLISH_APPENDIX = re.compile(
    r'Bãi\s*bỏ\s+Phụ\s+lục\s+([IVXL\d]+|[A-Z]+)',
    re.IGNORECASE,
)

R_SUPPLEMENT_APPENDIX = re.compile(
    r'Bổ\s*sung\s+Phụ\s+lục\s+([IVXL\d]+|[A-Z]+)\s+vào\s+sau\s+Phụ\s+lục\s+([IVXL\d]+|[A-Z]+)',
    re.IGNORECASE,
)

R_TARGET_LAW_CTX = re.compile(
    r'Sửa\s*đổi,\s*bổ\s*sung\s+(?:một\s+số\s+điều|các\s+điều)\s+(?:của\s+)?'
    r'(?:Luật|Nghị\s*định|Thông\s*tư)\s+(?:số\s+)?(\d+/\d+/[A-ZĐ]+(?:\d+)?(?:-[A-ZĐ]+(?:\d+)?)*)',
    re.IGNORECASE,
)


def extract_amendments(content: str) -> List[ExtractedAmendment]:
    if not content or len(content) < 50:
        return []

    results: List[ExtractedAmendment] = []
    lines = content.split('\n')
    full_text = content

    global_target = _detect_global_target(full_text)

    for m in R_PARTIAL_ABOLISH.finditer(full_text):
        target_doc = m.group(1)
        excepted_text = m.group(2)
        line_no = full_text[:m.start()].count('\n')
        for art_m in re.finditer(r'Điều\s+(\d+)', excepted_text, re.IGNORECASE):
            results.append(_make(
                "abolished_partial", target_doc,
                [AmendmentTarget(article=int(art_m.group(1)))],
                description=m.group(0)[:200],
                content=m.group(0),
                line_start=line_no, line_end=line_no,
            ))

    for line_no, line in enumerate(lines):
        stripped = line.strip()
        stripped = _strip_md(stripped)
        if not stripped or not _is_amendment(stripped):
            continue

        target_doc = global_target or _detect_target_in_line(stripped)

        for m in R_AMEND_CLAUSES.finditer(stripped):
            article = int(m.group(m.lastindex or 4) or 0)
            clauses = [g for g in m.groups()[:-1] if g and re.match(r'^\d+[a-zđ]*$', g, re.IGNORECASE)]
            for cl in clauses:
                results.append(_make(
                    "amended", target_doc,
                    [AmendmentTarget(article=article, clause=cl)],
                    description=stripped[:200],
                    content=_get_block(lines, line_no),
                    line_start=line_no, line_end=line_no,
                ))

        for m in R_AMEND_ARTICLE.finditer(stripped):
            art = int(m.group(1))
            if _dup(results, "amended", art):
                continue
            results.append(_make(
                "amended", target_doc,
                [AmendmentTarget(article=art)],
                description=stripped[:200],
                content=_get_block(lines, line_no),
                line_start=line_no, line_end=line_no,
            ))

        for m in R_AMEND_POINT.finditer(stripped):
            results.append(_make(
                "amended", target_doc,
                [AmendmentTarget(article=int(m.group(3)), clause=m.group(2), point=m.group(1))],
                description=stripped[:200],
                content=_get_block(lines, line_no),
                line_start=line_no, line_end=line_no,
            ))

        for m in R_AMEND_MULTI.finditer(stripped):
            article = int(m.group(1))
            subs = _extract_sub_clauses(lines, line_no, article)
            if subs:
                for s in subs:
                    sub_content = s.get("content", "")
                    results.append(_make(
                        "amended", target_doc, [s["target"]],
                        description=stripped[:200],
                        content=sub_content,
                        line_start=line_no, line_end=line_no,
                    ))

        for m in R_AMEND_FIRST_PARA.finditer(stripped):
            results.append(_make(
                "amended", target_doc,
                [AmendmentTarget(article=int(m.group(2)), clause=m.group(1), special="doan_dau")],
                description=stripped[:200],
                content=_get_block(lines, line_no),
                line_start=line_no, line_end=line_no,
            ))

        for m in R_SUPPLEMENT_CLAUSE.finditer(stripped):
            results.append(_make(
                "supplemented", target_doc,
                [AmendmentTarget(article=int(m.group(3)), clause=m.group(1))],
                description=stripped[:200],
                content=_get_block(lines, line_no),
                line_start=line_no, line_end=line_no,
            ))

        for m in R_REPLACE_CLAUSE.finditer(stripped):
            results.append(_make(
                "replaced_phrase", target_doc,
                [AmendmentTarget(article=int(m.group(4)), clause=m.group(3))],
                old_text=m.group(1), new_text=m.group(2),
                description=stripped[:200], content=stripped,
                line_start=line_no, line_end=line_no,
            ))

        for m in R_REPLACE_POINT.finditer(stripped):
            results.append(_make(
                "replaced_phrase", target_doc,
                [AmendmentTarget(article=int(m.group(5)), clause=m.group(4), point=m.group(3))],
                old_text=m.group(1), new_text=m.group(2),
                description=stripped[:200], content=stripped,
                line_start=line_no, line_end=line_no,
            ))

        for m in R_ABOLISH_CLAUSE.finditer(stripped):
            results.append(_make(
                "abolished", target_doc,
                [AmendmentTarget(article=int(m.group(2)), clause=m.group(1))],
                description=stripped[:200],
                content=_get_block(lines, line_no),
                line_start=line_no, line_end=line_no,
            ))

        for m in R_ABOLISH_ARTICLE.finditer(stripped):
            results.append(_make(
                "abolished", target_doc,
                [AmendmentTarget(article=int(m.group(1)))],
                description=stripped[:200],
                content=_get_block(lines, line_no),
                line_start=line_no, line_end=line_no,
            ))

        for m in R_CHAPTER_TITLE.finditer(stripped):
            results.append(_make(
                "amended", target_doc,
                [AmendmentTarget(chapter=m.group(2), section=m.group(1), special="ten_muc")],
                description=stripped[:200],
                content=_get_block(lines, line_no),
                line_start=line_no, line_end=line_no,
            ))

        for m in R_AMEND_APPENDIX.finditer(stripped):
            appendix_num = m.group(1)
            subs = _extract_appendix_rows(lines, line_no, appendix_num)
            if subs:
                for s in subs:
                    special = s.get("special", f"PL{appendix_num}")
                    results.append(_make(
                        s["action"], target_doc,
                        [AmendmentTarget(special=special)],
                        description=s.get("desc", stripped[:200])[:200],
                        content=s.get("content", ""),
                        line_start=line_no, line_end=line_no,
                    ))
            else:
                results.append(_make(
                    "amended", target_doc,
                    [AmendmentTarget(special=f"PL{appendix_num}")],
                    description=stripped[:200],
                    content=_get_block(lines, line_no),
                    line_start=line_no, line_end=line_no,
                ))

        for m in R_AMEND_APPENDIX_ROW.finditer(stripped):
            appendix_num = _find_preceding_appendix(lines, line_no)
            if appendix_num:
                stt = m.group(1)
                results.append(_make(
                    "supplemented" if "Bổ sung" in stripped else "amended", target_doc,
                    [AmendmentTarget(special=f"PL{appendix_num}.{stt}")],
                    description=stripped[:200],
                    content=_get_block(lines, line_no),
                    line_start=line_no, line_end=line_no,
                ))

        for m in R_ABOLISH_APPENDIX_ROW.finditer(stripped):
            appendix_num = _find_preceding_appendix(lines, line_no)
            if appendix_num:
                stt = m.group(1)
                results.append(_make(
                    "abolished", target_doc,
                    [AmendmentTarget(special=f"PL{appendix_num}.{stt}")],
                    description=stripped[:200],
                    content=stripped,
                    line_start=line_no, line_end=line_no,
                ))

        for m in R_ABOLISH_APPENDIX.finditer(stripped):
            results.append(_make(
                "abolished", target_doc,
                [AmendmentTarget(special=f"PL{m.group(1)}")],
                description=stripped[:200],
                content=_get_block(lines, line_no),
                line_start=line_no, line_end=line_no,
            ))

        for m in R_SUPPLEMENT_APPENDIX.finditer(stripped):
            results.append(_make(
                "supplemented", target_doc,
                [AmendmentTarget(special=f"PL{m.group(1)}")],
                description=stripped[:200],
                content=_get_block(lines, line_no),
                line_start=line_no, line_end=line_no,
            ))

        for m in R_REPLACE_APPENDIX.finditer(stripped):
            results.append(_make(
                "replaced_phrase", target_doc,
                [AmendmentTarget(special=f"PL{m.group(1)}")],
                description=stripped[:200],
                content=_get_block(lines, line_no),
                line_start=line_no, line_end=line_no,
            ))

    return results


def _detect_global_target(text: str) -> Optional[str]:
    for m in R_TARGET_LAW_CTX.finditer(text):
        return m.group(1)
    for m in R_DOC_NUMBER.finditer(text):
        return m.group(1)
    return None


def _detect_target_in_line(line: str) -> Optional[str]:
    m = R_DOC_NUMBER.search(line)
    return m.group(1) if m else None


def _is_amendment(line: str) -> bool:
    kw = ['sửa đổi, bổ sung', 'bãi bỏ', 'bổ sung khoản',
          'thay thế cụm từ', 'sửa đổi, bổ sung một số điều',
          'bổ sung, bãi bỏ', 'bổ sung, sửa đổi',
          'bổ sung số thứ tự', 'bãi bỏ số thứ tự',
          'sửa đổi, bổ sung phụ lục', 'bổ sung phụ lục']
    lower = line.lower()
    return any(k in lower for k in kw)


def _extract_sub_clauses(lines: List[str], start: int, article: int) -> List[dict]:
    targets = []
    current_clause = None
    current_start = None
    for i in range(start + 1, min(start + 40, len(lines))):
        line = _strip_md(lines[i].strip())
        if not line:
            continue
        m = R_SUB_AMEND.search(line)
        if m:
            if current_clause is not None and current_start is not None:
                content = _get_sub_block(lines, current_start, i - 1)
                targets.append({"target": AmendmentTarget(article=article, clause=current_clause), "content": content})
            current_clause = m.group(1)
            current_start = i
            continue
        if re.match(r'^\d+[.)]\s+(?:Sửa|Bãi|Bổ)', line, re.IGNORECASE):
            if current_clause is not None and current_start is not None:
                content = _get_sub_block(lines, current_start, i - 1)
                targets.append({"target": AmendmentTarget(article=article, clause=current_clause), "content": content})
            break
    if current_clause is not None and current_start is not None:
        content = _get_sub_block(lines, current_start, min(start + 40, len(lines)) - 1)
        targets.append({"target": AmendmentTarget(article=article, clause=current_clause), "content": content})
    return targets


def _extract_appendix_rows(lines: List[str], start: int, appendix_num: str) -> List[dict]:
    results = []
    ROW_ITEM = re.compile(r'[a-zđ]\)\s*(.+)', re.IGNORECASE)
    for i in range(start + 1, min(start + 40, len(lines))):
        line = _strip_md(lines[i].strip())
        if not line:
            continue
        if re.match(r'^\d+[.)]\s+(?:Sửa|Bãi|Bổ)', line, re.IGNORECASE):
            break
        m = ROW_ITEM.match(line)
        if not m:
            continue
        sub = m.group(1)
        rm = R_AMEND_APPENDIX_ROW.search(sub)
        if rm:
            action = "supplemented" if "Bổ sung" in sub else "amended"
            content = _get_block(lines, i)
            stt = rm.group(1)
            special = f"PL{appendix_num}.{stt}"
            results.append({"action": action, "desc": sub, "content": content, "special": special})
            continue
        rm = R_ABOLISH_APPENDIX_ROW.search(sub)
        if rm:
            stt = rm.group(1)
            special = f"PL{appendix_num}.{stt}"
            results.append({"action": "abolished", "desc": sub, "content": sub, "special": special})
    return results


def _find_preceding_appendix(lines: List[str], line_no: int) -> Optional[str]:
    for i in range(line_no - 1, max(line_no - 20, 0), -1):
        stripped = _strip_md(lines[i].strip())
        m = R_AMEND_APPENDIX.search(stripped)
        if m:
            return m.group(1)
    return None


def _get_sub_block(lines: List[str], start: int, end: int) -> str:
    buf = []
    for i in range(start + 1, end + 1):
        stripped = _strip_md(lines[i].strip())
        if re.match(r'^[a-zđ]\)\s+(?:Sửa|Bãi|Bổ)', stripped, re.IGNORECASE):
            break
        if re.match(r'^\d+[.)]\s+(?:Sửa|Bãi|Bổ)', stripped, re.IGNORECASE):
            break
        buf.append(lines[i])
    result = '\n'.join(buf).strip()
    cutoff = re.search(
        r'["\u201d]\.?\s*\d+\\?\.[)\s]?\s+(?:Sửa|Bãi|Bổ)',
        result, re.IGNORECASE,
    )
    if cutoff:
        result = result[:cutoff.start()].strip()
    return result[:2000]


def _strip_md(text: str) -> str:
    """Strip markdown escaping artifacts (\\., \\*, etc.) from text."""
    return re.sub(r'\\([.\-*_])', r'\1', text)


def _get_block(lines: List[str], line_no: int) -> str:
    buf = []
    for i in range(line_no + 1, min(line_no + 60, len(lines))):
        stripped = lines[i].strip()
        stripped = _strip_md(stripped)

        if re.match(r'^\d+[.)]\s+(?:Sửa|Bãi|Bổ|Thay)', stripped, re.IGNORECASE):
            break
        if re.match(r'^(?:Điều|Chương|Mục)\s+\d+', stripped):
            break
        if re.match(r'^[a-zđ]\)\s+(?:Sửa|Bãi|Bổ)', stripped, re.IGNORECASE):
            break

        buf.append(lines[i])

    result = '\n'.join(buf).strip()

    cutoff = re.search(
        r'["\u201d]\.?\s*\d+\\?\.[)\s]?\s+(?:Sửa|Bãi|Bổ)',
        result, re.IGNORECASE,
    )
    if cutoff:
        result = result[:cutoff.start()].strip()
    return result[:2000]


def _dup(results: List[ExtractedAmendment], action: str, article: int) -> bool:
    return any(
        r.action == action and any(t.article == article and t.clause is None for t in r.targets)
        for r in results
    )


def _make(action: str, target_doc: Optional[str], targets: List[AmendmentTarget],
          old_text: str = None, new_text: str = None,
          description: str = "", content: str = "",
          line_start: int = 0, line_end: int = 0) -> ExtractedAmendment:
    return ExtractedAmendment(
        action=action, target_doc_number=target_doc,
        targets=targets, old_text=old_text, new_text=new_text,
        description=description, content=content,
        line_start=line_start, line_end=line_end,
    )


_ROMAN_MAP = {
    'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7,
    'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13,
    'xiv': 14, 'xv': 15, 'xvi': 16, 'xvii': 17, 'xviii': 18,
}


def _parse_roman(s: str) -> Optional[int]:
    return _ROMAN_MAP.get(s.strip().lower())


def extract_amendment_effective_dates(
    enf_text: str, default_date: Optional[str] = None
) -> dict:
    """Parse enforcement text → map {article_key: effective_date}.

    Handles patterns like:
      \"Luật cũ hết hiệu lực kể từ ngày X, trừ Điều Y...hết hiệu lực từ ngày Z\"

    Returns dict: {\"D7\": \"2026-07-01\", \"PL4\": \"2026-07-01\", ...}
    Keys are \"D{article}\", \"K{clause}\", \"PL{appendix}\" for lookup.
    """
    from helpers.metadata_extractor import parse_vietnamese_date

    result: dict = {}
    if not enf_text:
        return result

    # Find main abolition date: "hết hiệu lực kể từ ngày X"
    main_date = default_date
    if not main_date:
        for m in re.finditer(
            r'(?:Luật|Nghị\s+định|Thông\s+tư|Quyết\s+định).*?hết\s+hiệu\s+lực\s+kể\s+từ\s+ngày\s+'
            r'(\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}|\d{2}/\d{2}/\d{4})',
            enf_text, re.IGNORECASE
        ):
            main_date = parse_vietnamese_date(m.group(0))
            break

    # Find exception dates: "trừ Điều X...hết hiệu lực kể từ ngày Y"
    for m in re.finditer(
        r'trừ\s+(.+?)\s+hết\s+hiệu\s+lực\s+kể\s+từ\s+ngày\s+'
        r'(\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}|\d{2}/\d{2}/\d{4})',
        enf_text, re.IGNORECASE
    ):
        provisions = m.group(1).strip().rstrip(',;').strip()
        date = parse_vietnamese_date(m.group(0))

        if not date:
            continue

        # Extract articles from provisions
        for am in re.finditer(
            r'(?:các\s+)?[Đđ]iều\s+(\d+(?:\s*(?:[,;]|và)\s*\d+)*)',
            provisions, re.IGNORECASE
        ):
            for num in re.findall(r'\d+', am.group(1)):
                key = f"D{num}"
                if key not in result:
                    result[key] = date

        # Extract clauses
        for cm in re.finditer(
            r'[Kk]hoản\s+(\d+)\s+[Đđ]iều\s+(\d+)',
            provisions, re.IGNORECASE
        ):
            clause = cm.group(1)
            article = cm.group(2)
            key = f"D{article}.K{clause}"
            if key not in result:
                result[key] = date

        # Extract phụ lục
        for pm in re.finditer(
            r'[Pp]hụ\s+[Ll]ục\s+([IVXLCDM\d]+)',
            provisions, re.IGNORECASE
        ):
            pl = pm.group(1).strip()
            roman = _parse_roman(pl)
            key = f"PL{roman or pl}"
            if key not in result:
                result[key] = date

    return result
