"""
SiteParser — Parse listing + document detail từ SITE_CRAWL_RULES.

Dùng chung cho tất cả site, config-driven.
"""
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from services.structure_parser import StructureParser

logger = logging.getLogger(__name__)


def _clean_url(href: str, base_url: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        scheme = urlparse(base_url).scheme
        return f"{scheme}:{href}"
    if href.startswith("/"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{href}"
    return href


def _extract_year_from_date(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    m = re.search(r"\b(19|20)\d{2}\b", date_str)
    return int(m.group()) if m else None


class SiteParser:
    """Parse document detail + listing page dùng selector từ config."""

    def __init__(self, site_rules: Dict):
        self.rules = site_rules

    @staticmethod
    def _find_first(soup: BeautifulSoup, selectors: List[Dict]) -> Optional[str]:
        for sel in selectors:
            tag = sel.get("tag")
            cls = sel.get("class")
            elem_id = sel.get("id")
            text_before = sel.get("text_before")
            try:
                if text_before:
                    for td in soup.find_all("td"):
                        if text_before.lower() in (td.get_text() or "").lower():
                            next_td = td.find_next_sibling("td")
                            if next_td:
                                return next_td.get_text(strip=True)
                elif cls:
                    el = soup.find(tag, class_=cls)
                    if el:
                        return el.get_text(strip=True)
                elif elem_id:
                    el = soup.find(tag, id=elem_id)
                    if el:
                        for junk in el(["script", "style"]):
                            junk.decompose()
                        return el.get_text(separator="\n", strip=True)
                else:
                    el = soup.find(tag)
                    if el:
                        return el.get_text(strip=True)
            except Exception:
                continue
        return None

    def parse_document(self, html: str, url: str) -> Optional[Dict]:
        try:
            soup = BeautifulSoup(html, "html.parser")
            doc_sel = self.rules.get("doc_selectors", {})

            title = self._find_first(soup, doc_sel.get("title", [])) or "Không có tiêu đề"
            doc_number = self._find_first(soup, doc_sel.get("doc_number", []))
            doc_type = self._find_first(soup, doc_sel.get("doc_type", []))
            issued_date = self._find_first(soup, doc_sel.get("issued_date", []))
            effective_date = self._find_first(soup, doc_sel.get("effective_date", []))
            issuing_authority = self._find_first(soup, doc_sel.get("issuing_authority", []))
            signer = self._find_first(soup, doc_sel.get("signer", []))
            status = self._find_first(soup, doc_sel.get("status", []))
            gazette_date = self._find_first(soup, doc_sel.get("gazette_date", []))
            gazette_number = self._find_first(soup, doc_sel.get("gazette_number", []))

            content = None
            for sel in doc_sel.get("content", []):
                tag = sel.get("tag")
                cls = sel.get("class")
                eid = sel.get("id")
                try:
                    el = (
                        soup.find(tag, id=eid) if eid
                        else soup.find(tag, class_=cls) if cls
                        else soup.find(tag)
                    )
                    if el and el.get_text(strip=True):
                        for junk in el(["script", "style"]):
                            junk.decompose()
                        content = el.get_text(separator="\n")
                        break
                except Exception:
                    continue

            if not content:
                body = soup.find("body")
                if body:
                    for junk in body(["script", "style", "nav", "header", "footer"]):
                        junk.decompose()
                    content = body.get_text(separator="\n")
                else:
                    content = ""

            # MỚI: Parse sections từ HTML (structure tree)
            sections = None
            struct_parser = StructureParser()
            for sel in doc_sel.get("content", []):
                tag = sel.get("tag")
                cls = sel.get("class")
                eid = sel.get("id")
                try:
                    container = (
                        soup.find(tag, id=eid) if eid
                        else soup.find(tag, class_=cls) if cls
                        else soup.find(tag)
                    )
                    if container and container.get_text(strip=True):
                        sections = struct_parser.parse(container)
                        if sections:
                            break
                except Exception:
                    continue
            if not sections:
                body = soup.find("body")
                if body:
                    sections = struct_parser.parse(body)

            doc_id = re.sub(r"[^a-zA-Z0-9_-]", "_", url.split("/")[-1].replace(".aspx", "").replace(".html", ""))
            if not doc_id:
                doc_id = re.sub(r"[^a-zA-Z0-9_-]", "_", urlparse(url).path.strip("/").replace("/", "_"))

            return {
                "doc_id": doc_id,
                "title": title,
                "doc_number": doc_number,
                "doc_type": doc_type,
                "issued_date": issued_date,
                "effective_date": effective_date,
                "issuing_authority": issuing_authority,
                "signer": signer,
                "status": status,
                "gazette_date": gazette_date,
                "gazette_number": gazette_number,
                "content": content,
                "sections": sections,
                "url": url,
                "year_published": (
                    _extract_year_from_date(issued_date)
                    or _extract_year_from_date(effective_date)
                ),
            }
        except Exception as e:
            logger.error(f"Error parsing document {url}: {e}")
            return None

    def extract_listing_links(self, html: str, base_url: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        found: List[str] = []
        href_pattern = self.rules.get("link_href_pattern", r"/van-ban/")

        for sel in self.rules.get("list_selectors", []):
            container = soup.find(sel["tag"], class_=sel.get("class"))
            if container:
                for a in container.find_all(sel.get("link_tag", "a"), href=True):
                    href = a["href"]
                    if re.search(href_pattern, href):
                        full = _clean_url(href, base_url)
                        if full not in found:
                            found.append(full)
                if found:
                    return found

        for a in soup.find_all("a", href=re.compile(href_pattern)):
            full = _clean_url(a["href"], base_url)
            if full not in found:
                found.append(full)
        return found
