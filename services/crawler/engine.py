"""
CrawlerEngine — Abstract base cho tất cả engine crawl.
"""
from abc import ABC, abstractmethod
from typing import Optional


class CrawlerEngine(ABC):
    """Base class cho crawl engines (requests / FlareSolverr)."""

    @abstractmethod
    async def start(self):
        ...

    @abstractmethod
    async def fetch_listing(self, url: str) -> Optional[str]:
        """Fetch HTML của một trang danh sách."""
        ...

    @abstractmethod
    async def fetch_document(self, url: str) -> Optional[str]:
        """Fetch HTML của một trang chi tiết văn bản."""
        ...

    @abstractmethod
    async def close(self):
        """Giải phóng tài nguyên."""
        ...
