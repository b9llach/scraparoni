"""
🕸️ Scraparoni - Advanced LLM-Powered Web Scraper

Intelligent web scraping with local LLMs, dual-mode scraping engines,
and dynamic user-agent rotation.

Quick Start:
    >>> from scraparoni import Scraparoni
    >>> from pydantic import BaseModel, Field
    >>>
    >>> class Product(BaseModel):
    ...     title: str = Field(description="Product title")
    ...     price: str = Field(description="Product price")
    >>>
    >>> scraparoni = Scraparoni()
    >>> data = scraparoni.scrape("https://example.com", Product)
    >>> print(data.title, data.price)

Components:
    - Scraparoni: Main scraper orchestrator
    - PhantomScraper: Lightning-fast curl-cffi scraper
    - BrowserScraper: Full Playwright browser automation
    - Weaver: LLM-powered data extraction
        - ScraparoniAgent: Dynamic user-agent rotation
"""

__version__ = "1.0.0"
__author__ = "Scraparoni"
__description__ = "Advanced LLM-powered web scraper with dual-mode scraping"

# Core imports
from .core import Scraparoni, quick_scrape, ScraparoniResponse
from .scrapers import PhantomScraper, BrowserScraper, BaseScraper
from .extractor import ScraparoniExtractor
from .agents import ScraparoniAgent

__all__ = [
    # Main classes
    "Scraparoni",
    "ScraparoniResponse",
    "quick_scrape",
    # Scrapers
    "PhantomScraper",
    "BrowserScraper",
    "BaseScraper",
    # Extraction
    "ScraparoniExtractor",
    # Agents
    "ScraparoniAgent",
]


def banner():
    """Print Scraparoni banner"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║    🕸️  SCRAPARONI - Advanced LLM-Powered Web Scraper 🕸️           ║
    ║                                                           ║
    ║    • Lightning-fast curl-cffi with TLS fingerprinting     ║
    ║    • Full Playwright browser automation                   ║
    ║    • Local LLM-powered data extraction                    ║
    ║    • Dynamic user-agent rotation                          ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
