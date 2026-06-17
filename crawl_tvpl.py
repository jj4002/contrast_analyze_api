#!/usr/bin/env python3
"""
CRAWL THUVIENPHAPLUAT.VN DÙNG FLARESOLVERR → SUPABASE.

Yêu cầu FlareSolverr Docker chạy trước:
  docker run -d --name flaresolverr -p 8191:8191 flaresolverr/flaresolverr:latest

Quy trình:
  1. FlareSolverr engine bypass Cloudflare
  2. Fetch listing pages → extract document links
  3. Fetch từng document page qua FlareSolverr
  4. Extract content + metadata (copy từ UnifiedCrawlerService)
  5. Clean data qua helpers (data_cleaner, content_cleaner)
  6. Dedup + insert vào Supabase PostgreSQL (legal_documents)

Chỉ crawl 5 lĩnh vực: Lao động, Thuế, Bảo hiểm, Sở hữu trí tuệ, Bảo mật.

Usage:
  python crawl_tvpl.py --max-pages 3 --max-docs 100
  python crawl_tvpl.py --category lao-dong thue --max-pages 5
  python crawl_tvpl.py --keyword "bảo mật" --max-pages 3
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import logging
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# ── Force UTF-8 stdout ────────────────────────────────────────────────
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Project paths ─────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
PROGRESS_FILE = DATA_DIR / "tvpl_crawl_progress.json"

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_DIR / f"crawl_tvpl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("tvpl_crawl")

# ── Import project modules ────────────────────────────────────────────
from config import (
    TVPL_DOMAIN, TVPL_TARGET_CATEGORIES as TARGET_CATEGORIES,
    SUPABASE_URL, FLARESOLVERR_URL, DOC_NUMBER_RE,
)
from services.tvpl_database import (
    get_conn as get_pg_conn, close as close_pg,
    get_all_urls, check_duplicate, insert_document, get_total_docs,
)
from services.crawler.flaresolverr_engine import FlareSolverrEngine
from helpers.data_cleaner import clean_document
from helpers.content_cleaner import clean_content, has_garbage

# ══════════════════════════════════════════════════════════════════════
# TVPL CONTENT EXTRACTION (copy từ UnifiedCrawlerService)
# ══════════════════════════════════════════════════════════════════════

import unicodedata
from bs4 import BeautifulSoup

CONTENT_SELS = [
    "ctl00_Content_ThongTinVB_pnlDocContent",
    "toanvancontent",
    "fulltext",
    "ctl00_Content_ThongTinVB_divNoiDung",
    "ctl00_Content_ThongTinVB_divContent",
    "divContentDoc",
    "divNoiDung",
    "divContent",
]

LEGAL_KEYWORDS = [
    r"\bĐiều\s+\d+",
    r"\bKhoản\s+\d+",
    r"\bChương\s+[IVXL\d]",
    r"\bMục\s+\d+",
]

GARBAGE_PATTERNS = [
    r"\* Lưu trữ\b",
    r"\*[ *]*Ghi chú\*?",
    r"\* Ý kiến\b",
    r"\* Email\b",
    r"\* In\b",
    r"Hỏi đáp pháp luật",
    r"Pháp Luật (?:Thuế|Doanh Nghiệp)",
    r"Bản án liên quan",
    r"BannerTuyenDung",
]

BAN_DICH_PATTERNS = [
    r"Ngôn\s*ngữ\s*:\s*Tiếng\s*Anh",
    r"Language\s*:\s*English",
]
TVPL_COPYRIGHT = r"Bản\s*dịch\s*này\s*thuộc\s*quyền\s*sở\s*hữu"


def is_ban_dich(text: str, html: str) -> bool:
    """Kiểm tra văn bản là bản dịch tiếng Anh."""
    for pattern in BAN_DICH_PATTERNS:
        if re.search(pattern, html or "", re.IGNORECASE):
            return True
    if text and len(text) > 200:
        clean = re.sub(TVPL_COPYRIGHT, "", text, flags=re.IGNORECASE)
        words = re.findall(r'[a-zA-ZÀ-ỹ]+', clean)
        if words:
            en = sum(1 for w in words if re.match(r'^[a-zA-Z]+$', w))
            if en / len(words) > 0.6:
                return True
    return False


def _find_content_panel(soup) -> Optional[BeautifulSoup]:
    prelim_text_cache = {}
    for sel_id in CONTENT_SELS:
        panel = soup.find(id=sel_id)
        if not panel:
            continue
        text = panel.get_text(separator="\n")
        if len(text) < 100:
            continue
        gc = sum(1 for p in GARBAGE_PATTERNS if re.search(p, text))
        lc = sum(1 for p in LEGAL_KEYWORDS if re.search(p, text))
        if lc >= 1 and gc <= lc + 1:
            return panel
        prelim_text_cache[sel_id] = text

    best_id, best_text = None, ""
    for sel_id in CONTENT_SELS:
        panel = soup.find(id=sel_id)
        if not panel:
            continue
        text = prelim_text_cache.get(sel_id) or panel.get_text(separator="\n")
        if len(text) > len(best_text):
            best_text = text
            best_id = sel_id
    if best_id and len(best_text) >= 200:
        logger.warning(f"Fallback content panel '{best_id}' ({len(best_text)} chars)")
        return soup.find(id=best_id)
    return None


def _is_content_valid(text: str) -> bool:
    if not text or len(text.strip()) < 100:
        return False
    has_legal = any(re.search(p, text) for p in LEGAL_KEYWORDS)
    gc = sum(1 for p in GARBAGE_PATTERNS if re.search(p, text))
    if has_legal:
        return True
    if gc == 0:
        return True
    if len(text) > 4000 and gc <= 4:
        return True
    return False


def extract_tvpl_content(html: str) -> Optional[str]:
    """Extract nội dung chính từ TVPL document page."""
    soup = BeautifulSoup(html, "html.parser")
    panel = _find_content_panel(soup)
    if not panel:
        logger.warning("Content panel not found")
        return None
    for script in panel(["script", "style"]):
        script.decompose()
    text = panel.get_text(separator="\n")
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r" +", " ", text)
    if len(text) < 100 or not _is_content_valid(text):
        return None
    return text


def extract_tvpl_content_fallback(html: str, url: str = "") -> Optional[str]:
    """Fallback: extract từ toàn body sau khi bỏ noise tags."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer",
                      "noscript", "iframe", "form", "select", "button",
                      "input", "textarea", "img", "svg", "canvas"]):
        tag.decompose()
    body = soup.find("body") or soup
    text = body.get_text(separator="\n")
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r" +", " ", text)
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) >= 3]
    text = "\n".join(lines)
    if len(text) < 200 or not _is_content_valid(text):
        return None
    logger.info(f"Full-body fallback extracted {len(text)} chars for {url[:80]}")
    return text


def extract_tvpl_metadata(html: str, doc_id: str = "") -> Dict[str, Optional[str]]:
    """Extract metadata từ HTML (copy từ UnifiedCrawlerService)."""
    soup = BeautifulSoup(html, "html.parser")
    meta = {
        "title": None, "doc_number": None, "doc_type": None,
        "issued_date": None, "effective_date": None,
        "issuing_authority": None, "signer": None,
        "category": None, "expiry_date": None,
        "year_published": None,
    }

    def _td_after(label: str) -> Optional[str]:
        td = soup.find("td", string=lambda s: s and label in s.strip() if s else False)
        if td and td.find_next_sibling("td"):
            return td.find_next_sibling("td").get_text(strip=True)
        b = soup.find("b", string=lambda s: s and label in s.strip() if s else False)
        if b and b.parent and b.parent.name == "td" and b.parent.find_next_sibling("td"):
            return b.parent.find_next_sibling("td").get_text(strip=True)
        return None

    def _clean_title_tag(text: str) -> str:
        return re.sub(r"\s*[-–—]?\s*Thư\s*viện\s*Pháp\s*luật\s*$", "", text).strip()

    def _title_matches_slug(title: str, slug: str) -> bool:
        if not title or not slug:
            return True
        def strip_vn(s: str) -> str:
            return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        words = set(re.findall(r"[a-zA-ZĐđ]+", slug.lower().replace("-", " ")))
        sig = {w for w in words if len(w) >= 4}
        if not sig:
            return True
        return any(w in strip_vn(title).lower() for w in sig)

    def _looks_like_authority(text: str) -> bool:
        text = text.strip()
        upper = sum(1 for c in text if c.isupper() or c in "ẮẤẾỐỒỔỠỘỞỜỚỢỨỰỬỦỤỊÍÌỈĨ")
        return upper > len(text) * 0.7 and not re.search(r"\d", text) and len(text) < 80

    thi = soup.select_one("#divThuocTinh")
    if thi:
        h1 = thi.find("h1")
        if h1:
            t = h1.get_text(strip=True)
            if not _looks_like_authority(t) and _title_matches_slug(t, doc_id):
                meta["title"] = t
    if not meta["title"]:
        title_el = soup.find("title")
        if title_el:
            t = _clean_title_tag(title_el.get_text(strip=True))
            if t and len(t) > 10 and _title_matches_slug(t, doc_id):
                meta["title"] = t
    if not meta["title"] and doc_id:
        fallback = doc_id.replace("_", " ").replace("-", " ")
        fallback = re.sub(r"\s+\d{5,}$", "", fallback).strip().title()
        fallback = re.sub(r"\bNd\b", "NĐ", fallback)
        fallback = re.sub(r"\bCp\b", "CP", fallback)
        fallback = re.sub(r"\bQh\b", "QH", fallback)
        if fallback and len(fallback) > 5:
            meta["title"] = fallback[:200]

    meta["doc_number"] = _td_after("Số hiệu:")
    meta["doc_type"] = _td_after("Loại văn bản:")
    meta["issued_date"] = _td_after("Ngày ban hành:")
    raw_eff = _td_after("Ngày hiệu lực:")
    meta["effective_date"] = None if raw_eff and raw_eff.strip().lower() in ("đã biết", "") else raw_eff
    meta["issuing_authority"] = _td_after("Nơi ban hành:")
    meta["signer"] = _td_after("Người ký:")
    meta["category"] = _td_after("Lĩnh vực:")
    meta["expiry_date"] = _td_after("Ngày hết hiệu lực:")

    raw_date = meta["issued_date"] or meta["effective_date"]
    if raw_date:
        try:
            if "/" in raw_date:
                parts = raw_date.split("/")
                if len(parts) == 3:
                    meta["year_published"] = int(parts[-1])
            else:
                meta["year_published"] = int(raw_date[:4])
        except (ValueError, IndexError):
            pass

    return meta


def extract_tvpl_listing_links(html: str) -> List[str]:
    """Extract tất cả link văn bản từ trang danh sách TVPL."""
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    href_pattern = re.compile(r"/van-ban/[^\"'?]+\.aspx$")

    for container in soup.find_all("p", class_="nqTitle"):
        for a in container.find_all("a", href=True):
            href = a["href"]
            if href_pattern.search(href):
                full = f"https://{TVPL_DOMAIN}{href}" if href.startswith("/") else href
                if full not in links:
                    links.append(full)
    if links:
        return links

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href_pattern.search(href):
            full = f"https://{TVPL_DOMAIN}{href}" if href.startswith("/") else href
            if full not in links:
                links.append(full)
    return links


# ══════════════════════════════════════════════════════════════════════
# CRAWLER ENGINE — FlareSolverr-based (giống test_crawl_tvpl.py)
# ══════════════════════════════════════════════════════════════════════

POLITE_DELAY = (5.0, 8.0)  # seconds between doc requests
TARGET_YEARS = set(range(2004, 2027))  # 2004-2026


class TvplCrawler:
    def __init__(self, max_pages: int = 3, max_docs: int = 99999,
                 keyword: str = "", category_filter: Optional[List[str]] = None):
        self.max_pages = max_pages
        self.max_docs = max_docs
        self.keyword = keyword
        self.category_filter = category_filter or list(TARGET_CATEGORIES.keys())
        self.engine: Optional[FlareSolverrEngine] = None
        self.processed_urls: Set[str] = set()
        self.crawled_count: int = 0
        self.skipped_ban_dich: int = 0
        self.skipped_year: int = 0
        self.failed: int = 0
        self.success: int = 0

    def _load_processed_urls(self):
        try:
            self.processed_urls = get_all_urls()
            logger.info(f"Loaded {len(self.processed_urls)} existing URLs from Supabase")
        except Exception as e:
            logger.warning(f"Could not load existing URLs: {e}")

    async def _crawl_document(self, url: str, cat_slug: str) -> bool:
        """Quy trình: FlareSolverr fetch → extract → clean → dedup → insert."""
        try:
            doc_html = await self.engine.fetch_document(url)
            if not doc_html:
                return False

            # Extract content (primary + fallback)
            content = extract_tvpl_content(doc_html)
            if not content:
                content = extract_tvpl_content_fallback(doc_html, url)
            if not content or "Đang tải văn bản" in content:
                logger.warning(f"No valid content: {url[:80]}")
                return False

            # Check translation
            if is_ban_dich(content, doc_html):
                logger.info(f"SKIP (bản dịch): {url[:80]}")
                self.skipped_ban_dich += 1
                return True  # counted as processed

            # Extract metadata
            doc_id = re.sub(r"[^a-zA-Z0-9_-]", "_", url.split("/")[-1].split(".aspx")[0])
            meta = extract_tvpl_metadata(doc_html, doc_id=doc_id)

            # Year filter
            year = meta.get("year_published") or 0
            if year > 0 and year not in TARGET_YEARS:
                self.skipped_year += 1
                return True

            # Build raw doc
            raw = {
                "doc_id": doc_id,
                "title": meta.get("title") or "Văn bản pháp luật",
                "content": content,
                "url": url,
                "doc_number": meta.get("doc_number"),
                "doc_type": meta.get("doc_type"),
                "issued_date": meta.get("issued_date"),
                "effective_date": meta.get("effective_date"),
                "expiry_date": meta.get("expiry_date"),
                "signer": meta.get("signer"),
                "issuing_authority": meta.get("issuing_authority"),
                "category": meta.get("category") or cat_slug,
                "year_published": meta.get("year_published"),
            }

            # Clean
            cleaned = clean_document(raw)
            if cleaned.get("_skip"):
                logger.warning(f"Content invalid after clean: {url[:80]}")
                return False

            # Dedup (3-key)
            doc_number = cleaned.get("doc_number") or doc_id
            existing = check_duplicate(
                doc_number,
                cleaned.get("issued_date") or "",
                cleaned.get("signer") or "",
            )
            if existing:
                self.processed_urls.add(url)
                return True

            # Insert Supabase
            ok = insert_document(
                doc_id=doc_id,
                title=cleaned.get("title", raw["title"]),
                content=cleaned.get("content", content),
                doc_number=doc_number,
                doc_type=cleaned.get("doc_type"),
                issued_date=cleaned.get("issued_date"),
                effective_date=cleaned.get("effective_date"),
                url=url,
                category=cleaned.get("category") or cat_slug,
                year_published=cleaned.get("year_published"),
                signer=cleaned.get("signer"),
                issuing_authority=cleaned.get("issuing_authority"),
                expiry_date=cleaned.get("expiry_date"),
            )
            if not ok:
                return False

            self.processed_urls.add(url)
            self.crawled_count += 1
            self.success += 1
            logger.info(f"[{self.crawled_count}/{self.max_docs}] {cleaned.get('title', doc_id)[:80]}")
            return True

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return False

    async def crawl_category(self, cat_slug: str) -> None:
        cat_info = TARGET_CATEGORIES[cat_slug]
        cat_url = cat_info["url"]

        logger.info(f"{'='*60}")
        logger.info(f"Category: {cat_info['label']} ({cat_slug}) — area_id={cat_info['area_id']}")
        logger.info(f"{'='*60}")

        for page in range(1, self.max_pages + 1):
            if self.crawled_count >= self.max_docs:
                break

            page_url = cat_url if page == 1 else f"{cat_url}{'&' if '?' in cat_url else '?'}page={page}"
            logger.info(f"[{cat_slug}] Fetching listing page {page}")

            html = await self.engine.fetch_listing(page_url)
            if not html:
                logger.warning(f"Listing page {page} returned None")
                break

            links = extract_tvpl_listing_links(html)
            if not links:
                found = re.findall(r"https?://thuvienphapluat\.vn/van-ban/[^\"'\s?]+\.aspx", html)
                links = list(dict.fromkeys(found))

            new_links = [u for u in links if u not in self.processed_urls]
            self.processed_urls.update(new_links)
            logger.info(f"[{cat_slug}] p.{page}: {len(new_links)} new / {len(links)} total")

            if not links:
                break

            for doc_url in new_links:
                if self.crawled_count >= self.max_docs:
                    break

                delay = random.uniform(*POLITE_DELAY)
                await asyncio.sleep(delay)

                if not await self._crawl_document(doc_url, cat_slug):
                    self.failed += 1

            if page % 5 == 0:
                await asyncio.sleep(random.uniform(10, 20))

    async def crawl_keyword(self) -> None:
        if not self.keyword:
            return

        from urllib.parse import urlencode
        SEARCH_URL = f"https://{TVPL_DOMAIN}/page/tim-van-ban.aspx"

        logger.info(f"{'='*60}")
        logger.info(f"Keyword search: '{self.keyword}'")
        logger.info(f"{'='*60}")

        for page in range(1, self.max_pages + 1):
            if self.crawled_count >= self.max_docs:
                break

            params = {"keyword": self.keyword, "match": "True", "area": "0"}
            if page > 1:
                params["page"] = str(page)
            page_url = f"{SEARCH_URL}?{urlencode(params)}"

            logger.info(f"[search] Fetching page {page}")
            html = await self.engine.fetch_listing(page_url)
            if not html:
                break

            links = extract_tvpl_listing_links(html)
            if not links:
                found = re.findall(r"https?://thuvienphapluat\.vn/van-ban/[^\"'\s?]+\.aspx", html)
                links = list(dict.fromkeys(found))

            new_links = [u for u in links if u not in self.processed_urls]
            self.processed_urls.update(new_links)
            logger.info(f"[search] p.{page}: {len(new_links)} new / {len(links)} total")

            if not links:
                break

            slug = "bao-mat" if any(k in self.keyword.lower() for k in ["bảo mật", "bảo-mật"]) else "search"
            for doc_url in new_links:
                if self.crawled_count >= self.max_docs:
                    break
                delay = random.uniform(*POLITE_DELAY)
                await asyncio.sleep(delay)
                if not await self._crawl_document(doc_url, slug):
                    self.failed += 1

    async def run(self):
        logger.info("=" * 60)
        logger.info(f"TVPL CRAWL (FlareSolverr) — {datetime.now()}")
        logger.info(f"  FlareSolverr: {FLARESOLVERR_URL}")
        logger.info(f"  Supabase:     {SUPABASE_URL}")
        logger.info(f"  Categories:   {self.category_filter}")
        logger.info(f"  Max pages:    {self.max_pages}")
        logger.info(f"  Max docs:     {self.max_docs}")
        logger.info(f"  Target years: {min(TARGET_YEARS)}-{max(TARGET_YEARS)}")
        if self.keyword:
            logger.info(f"  Keyword:      {self.keyword}")
        logger.info("=" * 60)

        # Init FlareSolverr engine
        self.engine = FlareSolverrEngine(flaresolverr_url=FLARESOLVERR_URL)
        await self.engine.start()

        self._load_processed_urls()

        if self.keyword:
            await self.crawl_keyword()
        else:
            for cat_slug in self.category_filter:
                if cat_slug not in TARGET_CATEGORIES:
                    logger.warning(f"Unknown category: {cat_slug}")
                    continue
                if self.crawled_count >= self.max_docs:
                    break
                await self.crawl_category(cat_slug)
                if self.crawled_count < self.max_docs:
                    await asyncio.sleep(random.uniform(8, 15))

        await self.engine.close()

        total_docs = get_total_docs()
        logger.info("=" * 60)
        logger.info(f"CRAWL COMPLETE — {datetime.now()}")
        logger.info(f"  New ingested:    {self.crawled_count}")
        logger.info(f"  Success:         {self.success}")
        logger.info(f"  Failed:          {self.failed}")
        logger.info(f"  Skipped (dịch):  {self.skipped_ban_dich}")
        logger.info(f"  Skipped (year):  {self.skipped_year}")
        logger.info(f"  Total Supabase:  {total_docs}")
        logger.info("=" * 60)
        close_pg()


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="Crawl thuvienphapluat.vn → Supabase (FlareSolverr)")
    parser.add_argument("--max-pages", type=int, default=3, help="Max pages per category (default: 3)")
    parser.add_argument("--max-docs", type=int, default=99999, help="Max total documents")
    parser.add_argument("--category", type=str, nargs="*", default=None,
                        help=f"Categories: {', '.join(TARGET_CATEGORIES.keys())}")
    parser.add_argument("--keyword", type=str, default="", help="Search keyword instead of category")
    parser.add_argument("--list-categories", action="store_true", help="List categories and exit")
    args = parser.parse_args()

    if args.list_categories:
        print("\nAvailable categories:")
        for slug, info in TARGET_CATEGORIES.items():
            print(f"  {slug:20s} — {info['label']} (area_id={info['area_id']})")
        return

    if not FLARESOLVERR_URL:
        logger.error("FLARESOLVERR_URL not set in config/.env")
        logger.error("Start FlareSolverr: docker run -d --name flaresolverr -p 8191:8191 flaresolverr/flaresolverr:latest")
        return

    crawler = TvplCrawler(
        max_pages=args.max_pages,
        max_docs=args.max_docs,
        keyword=args.keyword,
        category_filter=args.category if args.category else None,
    )
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
