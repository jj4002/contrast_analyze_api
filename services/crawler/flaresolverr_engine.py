"""
FlareSolverrEngine — Dùng FlareSolverr để bypass Cloudflare Turnstile.

FlareSolverr chạy một real Chrome browser trong container Docker,
tự động giải Cloudflare JS challenge và Turnstile, trả về HTML + cookies.

Usage:
    docker run -d --name flaresolverr -p 8191:8191 flaresolverr/flaresolverr:latest
"""
import logging
import time
from typing import Optional

import requests

from .engine import CrawlerEngine

logger = logging.getLogger(__name__)

FLARESOLVERR_DEFAULT_URL = "http://localhost:8191/v1"
REQUEST_TIMEOUT = 120


class FlareSolverrEngine(CrawlerEngine):
    """Engine dùng FlareSolverr để crawl site có Cloudflare."""

    def __init__(
        self,
        flaresolverr_url: str = FLARESOLVERR_DEFAULT_URL,
        session_name: Optional[str] = None,
    ):
        base = flaresolverr_url.rstrip("/")
        if not base.endswith("/v1"):
            base += "/v1"
        self._base_url = base
        self._session_name = session_name or f"tvpl_{int(time.time())}"
        self._started = False
        self._last_cookies: dict = {}

    async def start(self):
        """Verify FlareSolverr is reachable."""
        try:
            health_url = self._base_url.replace("/v1", "/health")
            resp = requests.get(health_url, timeout=5)
            if resp.status_code == 200:
                logger.info(f"FlareSolverr ready at {self._base_url}")
                self._started = True
            else:
                logger.warning(f"FlareSolverr health check failed: {resp.status_code}")
        except requests.ConnectionError:
            logger.warning(
                f"FlareSolverr not reachable at {self._base_url}. "
                "Run: docker run -d -p 8191:8191 flaresolverr/flaresolverr:latest"
            )

    async def close(self):
        self._started = False
        logger.info("FlareSolverrEngine closed")

    async def fetch_listing(self, url: str) -> Optional[str]:
        return await self._request(url)

    async def fetch_document(self, url: str) -> Optional[str]:
        return await self._request(url)

    async def get_cookies(self) -> dict:
        return self._last_cookies

    def _request_sync(self, url: str) -> Optional[str]:
        """Sync request qua FlareSolverr."""
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": REQUEST_TIMEOUT * 1000,
            "session": self._session_name,
        }

        try:
            resp = requests.post(self._base_url, json=payload, timeout=REQUEST_TIMEOUT + 10)
            data = resp.json()
            solution = data.get("solution", {})

            if solution.get("status") != 200:
                logger.warning(f"FlareSolverr status {solution.get('status')} for {url[:80]}")
                return None

            html = solution.get("response", "")
            cookies = solution.get("cookies", [])
            self._last_cookies = {
                c["name"]: c["value"]
                for c in cookies
                if "name" in c
            }

            logger.info(
                f"[FlareSolverr] Fetched {len(html)} chars, "
                f"{len(self._last_cookies)} cookies, "
                f"cf_clearance={'YES' if 'cf_clearance' in self._last_cookies else 'NO'}"
            )
            return html

        except requests.Timeout:
            logger.warning(f"FlareSolverr timeout for {url[:80]}")
            return None
        except Exception as e:
            logger.warning(f"FlareSolverr error for {url[:80]}: {e}")
            return None

    async def _request(self, url: str) -> Optional[str]:
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._request_sync, url)
