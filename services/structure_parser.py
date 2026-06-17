import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@dataclass
class SectionNode:
    section_type: str
    number: Optional[str]
    heading: str
    content: str = ""
    children: List['SectionNode'] = field(default_factory=list)
    parent: Optional['SectionNode'] = None
    _html_parts: List[str] = field(default_factory=list)
    _finalized: bool = False

    def append_html(self, element: Tag):
        self._html_parts.append(str(element))

    def _all_html_parts(self) -> List[str]:
        parts = list(self._html_parts)
        for child in self.children:
            parts.extend(child._all_html_parts())
        return parts

    def finalize(self):
        if self._finalized or not self._html_parts:
            return
        self._finalized = True
        full_html = "".join(self._html_parts)
        for child in self.children:
            child_html = "".join(child._all_html_parts())
            if child_html not in full_html:
                full_html += "\n" + child_html
        soup = BeautifulSoup(full_html, "html.parser")
        self.content = soup.get_text(separator="\n").strip()

    @property
    def depth(self) -> int:
        return _SECTION_DEPTH.get(self.section_type, 99)

    def full_heading(self) -> str:
        if self.section_type == "khoan" and self.parent:
            return f"{self.parent.full_heading()} Khoản {self.number}"
        if self.section_type == "diem" and self.parent:
            return f"{self.parent.full_heading()} Điểm {self.number}"
        return self.heading


_SECTION_DEPTH = {
    "preamble": 0,
    "header": 0,
    "title_section": 0,
    "legal_basis": 0,
    "chuong": 1,
    "muc": 2,
    "dieu": 3,
    "khoan": 4,
    "diem": 5,
    "enforcement": 3,
    "phu_luc": 1,
    "signing": 99,
}

_SECTION_PATTERNS: List[Tuple[str, str, int]] = [
    ("chuong",  r'^(?:CHƯƠNG|Chương)\s+([IVXLCDM]+|\d+)', re.I),
    ("muc",     r'^(?:MỤC|Mục)\s+(\d+)', re.I),
    ("dieu",    r'^(?:ĐIỀU|Điều)\s+(\d+)', re.I),
    ("phu_luc", r'^(?:PHỤ LỤC|Phụ lục)(?:\s+(\d+))?', re.I),
    ("khoan",   r'^(\d+)\.\s', 0),
    ("diem",    r'^([a-zđ])\)\s', 0),
]

_SIGNING_PATTERNS = [
    r'^Nơi nhận:',
    r'^Ký\s+tên',
    r'^KT\.',
    r'^TM\.\s',
]

_CONTENT_TAGS = {'p', 'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                 'li', 'ul', 'ol', 'hr', 'pre', 'blockquote', 'div'}

# Document-type title patterns (all-caps, short, typically standalone line)
_TITLE_PATTERNS = [
    r'^(?:NGHỊ ĐỊNH|THÔNG TƯ|QUYẾT ĐỊNH|LUẬT|PHÁP LỆNH|THÔNG CÁO|CHỈ THỊ|CÔNG VĂN|THÔNG BÁO|HƯỚNG DẪN)\b',
]

_ENFORCEMENT_RE = re.compile(
    r'Điều\s+\d+\s*\.\s*Điều\s+khoản\s+thi\s+hành'
    r'|Điều\s+\d+\s*\.\s*Trách\s+nhiệm\s+và\s+hiệu\s+lực\s+thi\s+hành'
    r'|Điều\s+\d+\s*\.\s*Hiệu\s+lực\s+thi\s+hành'
    r'|Chương\s+[IVXLCDM]+\s+ĐIỀU\s+KHOẢN\s+THI\s+HÀNH'
    r'|Quyết\s+định\s+\(\s*[Đđ]iều\s+\d+\s*-\s*\d+\s*\)',
    re.IGNORECASE
)


def _is_doc_title(text: str) -> bool:
    cleaned = text.strip().upper()
    if len(cleaned) < 3 or len(cleaned) > 120:
        return False
    return any(re.match(p, cleaned) for p in _TITLE_PATTERNS)


def _is_likely_enforcement(heading: str) -> bool:
    return bool(_ENFORCEMENT_RE.search(heading))

_CONTENT_SELECTORS = [
    {"id": "toanvancontent"},
    {"class": "content1"},
    {"id": "fulltext"},
    {"class": "content"},
    {"id": "ctl00_Content_ThongTinVB_pnlDocContent"},
    {"class": "detail-content"},
    {"class": "fulltext"},
    {"id": "ToFullText"},
]


class StructureParser:

    def extract_sections(self, soup_or_html) -> List[SectionNode]:
        if isinstance(soup_or_html, str):
            # Detect actual HTML tags (e.g. <p>, <div>) vs literal < characters
            if re.search(r'<\s*[a-zA-Z_/]', soup_or_html):
                soup = BeautifulSoup(soup_or_html, "html.parser")
            else:
                return self.parse_plain_text(soup_or_html)
        else:
            soup = soup_or_html
        for sel in _CONTENT_SELECTORS:
            container = None
            if "id" in sel:
                container = soup.find(id=sel["id"])
            elif "class" in sel:
                container = soup.find(class_=sel["class"])
            if container and container.get_text(strip=True):
                sections = self.parse(container)
                if sections:
                    return sections
        body = soup.find("body")
        if body:
            sections = self.parse(body)
            if sections:
                return sections
        # Fallback: HTML path yielded nothing → try plain text parsing
        if isinstance(soup_or_html, str):
            return self.parse_plain_text(soup_or_html)
        return []

    def parse_plain_text(self, text: str) -> List[SectionNode]:
        """Parse plain text (no HTML) by splitting lines and matching section patterns."""
        lines = text.split("\n")
        root = SectionNode("root", None, "")
        stack: List[SectionNode] = [root]
        current_sec: Optional[SectionNode] = None
        seen_main_structure = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_sec:
                    current_sec._html_parts.append(line)
                continue

            cleaned = stripped.replace('**', '').replace('\\.', '.').replace('\\-', '-').replace('\\+', '+').replace('|', ' ')
            matched = False

            for type_name, pattern, flags in _SECTION_PATTERNS:
                m = re.match(pattern, cleaned, flags)
                if m:
                    num = m.group(1)
                    depth = _SECTION_DEPTH.get(type_name, 99)
                    sec = SectionNode(type_name, num, cleaned)
                    sec._html_parts.append(line)
                    sec._finalized = True
                    sec.content = cleaned

                    if type_name == "legal_basis":
                        root.children.append(sec)
                        sec.parent = root
                        stack = [root, sec]
                        current_sec = sec
                        matched = True
                        break

                    if type_name == "phu_luc":
                        root.children.append(sec)
                        sec.parent = root
                        stack = [root, sec]
                        current_sec = sec
                        matched = True
                        break

                    if type_name in ("dieu", "chuong", "muc"):
                        seen_main_structure = True

                    while stack and stack[-1].depth >= depth:
                        stack.pop()
                    parent = stack[-1] if stack else root
                    parent.children.append(sec)
                    sec.parent = parent if parent != root else None
                    stack.append(sec)
                    current_sec = sec
                    matched = True
                    break

            if matched:
                continue

            # Check title_section before signing/preable
            if not seen_main_structure and _is_doc_title(stripped):
                sec = SectionNode("title_section", None, cleaned)
                sec._html_parts.append(line)
                sec._finalized = True
                sec.content = cleaned
                root.children.append(sec)
                sec.parent = root
                stack = [root, sec]
                current_sec = sec
                continue

            is_signing = any(re.match(p, cleaned) for p in _SIGNING_PATTERNS)
            if is_signing:
                sec = SectionNode("signing", None, cleaned)
                sec._html_parts.append(line)
                sec._finalized = True
                sec.content = cleaned
                root.children.append(sec)
                sec.parent = root
                current_sec = sec
                continue

            if current_sec:
                current_sec._html_parts.append(line)
                if current_sec.content:
                    current_sec.content += "\n" + cleaned
                else:
                    current_sec.content = cleaned
            else:
                sec = SectionNode("header", None, "")
                sec._html_parts.append(line)
                sec.content = cleaned
                root.children.append(sec)
                sec.parent = root
                current_sec = sec

        self._finalize_plain_tree(root)
        self._mark_enforcement(root)
        return root.children

    def _finalize_plain_tree(self, node: SectionNode):
        """After building plain-text tree, propagate children content into parent content."""
        for child in node.children:
            self._finalize_plain_tree(child)
            if child.content and node.content:
                if child.content not in node.content:
                    node.content += "\n" + child.content
            elif child.content:
                node.content = child.content

    def parse(self, container: Tag) -> List[SectionNode]:
        elements = self._collect_elements(container)
        return self._build_tree(elements)

    def _collect_elements(self, container: Tag):
        results = []
        seen = set()
        for el in container.find_all(_CONTENT_TAGS, recursive=True):
            if id(el) in seen:
                continue
            seen.add(id(el))
            if el.name in ('script', 'style', 'nav', 'header', 'footer'):
                continue
            if el.name == 'div':
                child_blocks = el.find_all(
                    ['p', 'table', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol'],
                    recursive=False
                )
                if child_blocks:
                    continue
            text = el.get_text(strip=True)
            if not text:
                continue
            matched = False
            for type_name, pattern, flags in _SECTION_PATTERNS:
                m = re.match(pattern, text, flags)
                if m:
                    num = m.group(1)
                    results.append((el, type_name, num))
                    matched = True
                    break
            if matched:
                continue
            is_signing = any(re.match(p, text) for p in _SIGNING_PATTERNS)
            if is_signing:
                results.append((el, "signing", None))
                continue
            results.append((el, None, None))
        return results

    def _build_tree(self, elements) -> List[SectionNode]:
        root = SectionNode("root", None, "")
        stack: List[SectionNode] = [root]
        current_sec: Optional[SectionNode] = None
        seen_main_structure = False  # chuong/dieu bắt đầu → không detect legal_basis/title nữa

        for el, type_name, number in elements:
            if type_name is None:
                text = el.get_text(strip=True)
                if not seen_main_structure and _is_doc_title(text):
                    type_name = "title_section"
                    number = None
                elif not seen_main_structure and self._is_legal_basis(text):
                    type_name = "legal_basis"
                    number = None

            if type_name is None:
                if current_sec:
                    current_sec.append_html(el)
                else:
                    sec = SectionNode("header", None, "")
                    root.children.append(sec)
                    sec.parent = root
                    current_sec = sec
                    current_sec.append_html(el)
                continue

            heading = el.get_text(strip=True)
            depth = _SECTION_DEPTH.get(type_name, 99)
            sec = SectionNode(type_name, number, heading)
            sec.append_html(el)

            if type_name in ("signing",):
                root.children.append(sec)
                sec.parent = root
                current_sec = sec
                continue

            if type_name in ("title_section", "legal_basis"):
                root.children.append(sec)
                sec.parent = root
                stack = [root, sec]
                current_sec = sec
                continue

            if type_name == "phu_luc":
                root.children.append(sec)
                sec.parent = root
                stack = [root, sec]
                current_sec = sec
                continue

            if type_name in ("dieu", "chuong", "muc"):
                seen_main_structure = True

            while stack and stack[-1].depth >= depth:
                stack.pop()

            parent = stack[-1] if stack else root
            parent.children.append(sec)
            sec.parent = parent if parent != root else None
            stack.append(sec)
            current_sec = sec

        self._finalize_all(root)
        self._mark_enforcement(root)
        return root.children

    def _is_legal_basis(self, text: str) -> bool:
        return bool(re.match(r'^Căn cứ\s+(?:vào\s+)?(?:Luật|Pháp lệnh|Nghị quyết|Hiến pháp|Bộ luật)\s', text, re.I))

    def _mark_enforcement(self, root: SectionNode):
        """Mark enforcement sections based on heading patterns only."""
        all_dieu = []
        def _collect_dieu(node):
            if node.section_type == "dieu":
                all_dieu.append(node)
            for c in node.children:
                _collect_dieu(c)

        def _mark_dieu_deep(node):
            for c in node.children:
                if c.section_type == "dieu":
                    c.section_type = "enforcement"
                _mark_dieu_deep(c)

        # Phase 1: chapter heading matches "Chương X. ĐIỀU KHOẢN THI HÀNH"
        def _find_chapters(node):
            for child in node.children:
                if child.section_type == "chuong":
                    if _is_likely_enforcement(child.heading):
                        _mark_dieu_deep(child)
                    else:
                        _find_chapters(child)
                else:
                    _find_chapters(child)
        _find_chapters(root)

        # Collect remaining dieu
        _collect_dieu(root)

        # Phase 2: dieu heading matches specific enforcement patterns
        for node in all_dieu:
            if _is_likely_enforcement(node.heading):
                node.section_type = "enforcement"

        # Phase 3: short decision heading, check heading + first content sentence
        if not any(n.section_type == "enforcement" for n in all_dieu):
            for node in reversed(all_dieu):
                check_text = (node.heading or "") + " " + (node.content or "")[:300]
                if re.search(
                    r'(?:quyết\s+định|thông\s+tư|nghị\s+định|văn\s+bản)\s+này\s+có\s+hiệu\s+lực',
                    check_text, re.IGNORECASE,
                ):
                    node.section_type = "enforcement"
                    break

    def _finalize_all(self, node: SectionNode):
        for child in node.children:
            self._finalize_all(child)
        if node.section_type != "root":
            node.finalize()
