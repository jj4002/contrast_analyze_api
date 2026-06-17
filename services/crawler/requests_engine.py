"""
RequestsEngine — Crawl bằng requests với anti-detection.
- curl_cffi TLS impersonation (Chrome fingerprint)
- Rotate User-Agent, Accept-Language, Referer mỗi request
- Refresh session sau N requests để tránh cookie fingerprint
"""
import asyncio
import logging
import random
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .engine import CrawlerEngine

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
]

ACCEPT_LANGUAGES = [
    "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "vi,en-US;q=0.9,en;q=0.8",
    "en-US,en;q=0.9,vi;q=0.8",
]

CHROME_VERSIONS = ["chrome120", "chrome124", "chrome131"]


def _make_session(rotate: bool = False) -> requests.Session:
    try:
        from curl_cffi import requests as curl_requests
        session = curl_requests.Session()
        session.impersonate = random.choice(CHROME_VERSIONS)
        if rotate:
            logger.debug(f"curl_cffi session (impersonate={session.impersonate})")
    except ImportError:
        session = requests.Session()
        retry = Retry(total=2, backoff_factor=5, status_forcelist=[403, 429, 500, 502, 503, 504])
        adapter = HTTPAdapter(pool_connections=5, pool_maxsize=5, max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Cache-Control": random.choice(["no-cache", "max-age=0"]),
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": random.choice(["none", "same-origin", "cross-site"]),
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    })
    return session


class RequestsEngine(CrawlerEngine):
    """Engine requests với rotate header + session refresh."""

    def __init__(self, rotate_interval: int = 5):
        self.session = _make_session()
        self.semaphore = asyncio.Semaphore(3)
        self._started = False
        self._request_count = 0
        self._rotate_interval = rotate_interval

    async def start(self):
        self._started = True

    def _maybe_rotate(self):
        """Rotate headers mỗi request, refresh session sau N requests."""
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Referer": self.session.headers.get("Referer", "https://www.google.com/"),
            "Cache-Control": random.choice(["no-cache", "max-age=0"]),
            "Sec-Fetch-Site": random.choice(["none", "same-origin", "cross-site"]),
        })
        self._request_count += 1
        if self._request_count >= self._rotate_interval:
            try:
                self.session.close()
            except Exception:
                pass
            self.session = _make_session(rotate=True)
            self._request_count = 0

    def _set_referer(self, url: str):
        from urllib.parse import urlparse
        parsed = urlparse(url)
        ref = f"{parsed.scheme}://{parsed.netloc}/"
        self.session.headers["Referer"] = ref

    async def fetch_listing(self, url: str) -> Optional[str]:
        async with self.semaphore:
            try:
                self._maybe_rotate()
                self._set_referer(url)
                response = await asyncio.to_thread(
                    self.session.get, url, timeout=30, allow_redirects=True,
                )
                if response.status_code != 200:
                    logger.warning(f"Listing HTTP {response.status_code}: {url}")
                    return None
                return response.text
            except Exception as e:
                logger.warning(f"Listing failed: {url} — {e}")
                return None

    async def fetch_document(self, url: str) -> Optional[str]:
        async with self.semaphore:
            try:
                self._maybe_rotate()
                self._set_referer(url)
                response = await asyncio.to_thread(
                    self.session.get, url, timeout=30, allow_redirects=True,
                )
                if response.status_code != 200:
                    logger.warning(f"Doc HTTP {response.status_code}: {url}")
                    return None
                return response.text
            except Exception as e:
                logger.warning(f"Doc failed: {url} — {e}")
                return None

    async def close(self):
        try:
            self.session.close()
        except Exception:
            pass
        self._started = False
