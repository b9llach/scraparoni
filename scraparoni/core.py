"""
Scraparoni - Main Orchestrator
The core spider that weaves everything together
"""

import json
from typing import Type, Optional, List, Dict, Any, Union
from pydantic import BaseModel

from .agents import ScraparoniAgent
from .scrapers import PhantomScraper, BrowserScraper
from .extractor import ScraparoniExtractor


class ScraparoniResponse:
    """
    Wrapper for scrape results with convenient output methods
    """

    def __init__(self, data: BaseModel):
        self._data = data

    def dict(self) -> Dict[str, Any]:
        """Return as Python dict"""
        return self._data.model_dump()

    def json(self, indent: int = 2) -> str:
        """Return as formatted JSON string with double quotes"""
        return json.dumps(self._data.model_dump(), indent=indent)

    def model(self) -> BaseModel:
        """Return the raw Pydantic model"""
        return self._data

    def __repr__(self) -> str:
        return self.json()

    def __str__(self) -> str:
        return self.json()


class Scraparoni:
    """
    🕸️ Scraparoni - Advanced LLM-Powered Web Scraper

    Combines lightning-fast HTTP scraping with full browser automation,
    dynamic user-agent rotation, and intelligent LLM-based extraction.

    Features:
    - PhantomScraper: curl-cffi with TLS fingerprinting (bypasses Cloudflare)
    - BrowserScraper: Full Playwright automation for JS-heavy sites
    - ScraparoniExtractor: LLM-powered structured data extraction
    - ScraparoniAgent: Dynamic user-agent rotation
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-7B-Instruct-1M",
        prefer_desktop: bool = True,
        sticky_agent: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize Scraparoni web scraper

        Args:
            model_name: HuggingFace model for extraction
            prefer_desktop: Use desktop user-agents by default
            sticky_agent: Keep same user-agent for session
            verbose: Show detailed loading progress
        """
        if verbose:
            print("🕸️  Initializing Scraparoni...")

        self.agent = ScraparoniAgent(prefer_desktop=prefer_desktop, sticky=sticky_agent)
        self.phantom = PhantomScraper(agent=self.agent)
        self.weaver = ScraparoniExtractor(model_name=model_name, verbose=verbose)

        if verbose:
            print("✓ Scraparoni ready to weave!")

    # ========================================================================
    # HIGH-LEVEL SCRAPING METHODS
    # ========================================================================

    def scrape(
        self,
        url: str,
        schema: Type[BaseModel],
        instructions: Optional[str] = None,
        use_browser: bool = False,
        auto_fallback: bool = True,
        save_html: Optional[str] = None,
        **kwargs
    ) -> ScraparoniResponse:
        """
        Scrape URL and extract structured data (auto-selects scraper with fallback)

        Args:
            url: Target URL
            schema: Pydantic schema for extraction
            instructions: Additional extraction instructions
            use_browser: Force browser usage (default: False)
            auto_fallback: Auto-retry with BrowserScraper if extraction returns empty data (default: True)
            save_html: Optional path to save the HTML for debugging (e.g., "debug.html")
            **kwargs: Additional scraper arguments

        Returns:
            ScraparoniResponse with .json(), .dict(), .model() methods
        """
        # Fetch HTML
        if use_browser:
            html = self._fetch_with_browser(url, **kwargs)
        elif auto_fallback:
            try:
                html = self.phantom.fetch(url, **kwargs)
                # Quick check if HTML looks empty (likely JS-rendered)
                if len(html) < 500 or '<body' not in html.lower():
                    print("⚠️  HTML appears empty, retrying with BrowserScraper...")
                    html = self._fetch_with_browser(url, **kwargs)
            except Exception:
                html = self._fetch_with_browser(url, **kwargs)
        else:
            html = self.phantom.fetch(url, **kwargs)

        # Save HTML if requested
        if save_html:
            with open(save_html, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"✓ Saved HTML to {save_html} ({len(html)} chars)")

        # Extract data
        result = self.weaver.extract(html, schema, instructions)

        # Check if extraction is empty and retry with browser if needed
        if auto_fallback and not use_browser and self._is_empty_extraction(result):
            print("⚠️  Extraction returned empty data, retrying with BrowserScraper...")
            html = self._fetch_with_browser(url, **kwargs)
            if save_html:
                with open(save_html, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"✓ Updated HTML in {save_html} ({len(html)} chars)")
            result = self.weaver.extract(html, schema, instructions)

        return ScraparoniResponse(result)

    def _fetch_with_browser(self, url: str, **kwargs) -> str:
        """Helper to fetch HTML with BrowserScraper"""
        with BrowserScraper(agent=self.agent, headless=kwargs.pop('headless', True)) as browser:
            return browser.fetch(url, **kwargs)

    def scrape_with_phantom(
        self,
        url: str,
        schema: Type[BaseModel],
        instructions: Optional[str] = None,
        **kwargs
    ) -> BaseModel:
        """
        Fast scraping using PhantomScraper (curl-cffi)

        Args:
            url: Target URL
            schema: Pydantic extraction schema
            instructions: Custom extraction instructions
            **kwargs: PhantomScraper.fetch() arguments

        Returns:
            Extracted and validated data
        """
        html = self.phantom.fetch(url, **kwargs)

        return self.weaver.extract(html, schema, instructions)

    def scrape_with_browser(
        self,
        url: str,
        schema: Type[BaseModel],
        instructions: Optional[str] = None,
        wait_for: Optional[str] = None,
        headless: bool = True,
        **kwargs
    ) -> BaseModel:
        """
        Full browser scraping using BrowserScraper (Playwright)

        Args:
            url: Target URL
            schema: Pydantic extraction schema
            instructions: Custom extraction instructions
            wait_for: CSS selector to wait for
            headless: Run browser in headless mode
            **kwargs: BrowserScraper.fetch() arguments

        Returns:
            Extracted and validated data
        """
        with BrowserScraper(agent=self.agent, headless=headless) as browser:
            html = browser.fetch(url, wait_for=wait_for, **kwargs)

        return self.weaver.extract(html, schema, instructions)

    def scrape_with_interaction(
        self,
        url: str,
        schema: Type[BaseModel],
        interactions: List[Dict[str, Any]],
        instructions: Optional[str] = None,
        headless: bool = True,
    ) -> BaseModel:
        """
        Scrape with custom browser interactions (clicks, scrolls, etc.)

        Args:
            url: Target URL
            schema: Pydantic extraction schema
            interactions: List of interaction dicts (see BrowserScraper.fetch_with_interaction)
            instructions: Custom extraction instructions
            headless: Run browser in headless mode

        Returns:
            Extracted and validated data
        """
        with BrowserScraper(agent=self.agent, headless=headless) as browser:
            html = browser.fetch_with_interaction(url, interactions)

        return self.weaver.extract(html, schema, instructions)

    # ========================================================================
    # BATCH OPERATIONS
    # ========================================================================

    def scrape_many(
        self,
        urls: List[str],
        schema: Type[BaseModel],
        instructions: Optional[str] = None,
        use_browser: bool = False,
        **kwargs
    ) -> List[BaseModel]:
        """
        Scrape multiple URLs with same schema

        Args:
            urls: List of URLs to scrape
            schema: Pydantic extraction schema
            instructions: Custom extraction instructions
            use_browser: Use browser scraper
            **kwargs: Scraper arguments

        Returns:
            List of extracted data models
        """
        results = []
        total = len(urls)

        for i, url in enumerate(urls, 1):
            try:
                result = self.scrape(url, schema, instructions, use_browser, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"❌ Failed: {str(e)}")
                results.append(None)

        return results

    # ========================================================================
    # RAW METHODS (without LLM extraction)
    # ========================================================================

    def fetch_html(
        self,
        url: str,
        use_browser: bool = False,
        **kwargs
    ) -> str:
        """
        Fetch raw HTML without extraction

        Args:
            url: Target URL
            use_browser: Use browser scraper
            **kwargs: Scraper arguments

        Returns:
            Raw HTML string
        """
        if use_browser:
            with BrowserScraper(agent=self.agent) as browser:
                return browser.fetch(url, **kwargs)
        else:
            return self.phantom.fetch(url, **kwargs)

    def extract_from_html(
        self,
        html: str,
        schema: Type[BaseModel],
        instructions: Optional[str] = None,
    ) -> BaseModel:
        """
        Extract data from pre-fetched HTML

        Args:
            html: HTML content
            schema: Pydantic extraction schema
            instructions: Custom extraction instructions

        Returns:
            Extracted and validated data
        """
        return self.weaver.extract(html, schema, instructions)

    def analyze_html(
        self,
        html: str,
        prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """
        Run custom analysis prompt on HTML (no schema)

        Args:
            html: HTML content
            prompt: Custom analysis prompt
            temperature: LLM temperature

        Returns:
            Raw LLM response
        """
        return self.weaver.custom_prompt(html, prompt, temperature)

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _is_empty_extraction(self, result: BaseModel) -> bool:
        """
        Check if extraction returned mostly empty/None values
        (indicates JS-rendered content that PhantomScraper can't see)

        Args:
            result: Extracted Pydantic model

        Returns:
            True if extraction appears empty/failed
        """
        data = result.model_dump()
        values = list(data.values())

        if not values:
            return True

        # Count None/empty values
        none_count = sum(1 for v in values if v is None or v == "" or v == [] or v == {})

        # If 80%+ of fields are None/empty, consider it empty
        empty_ratio = none_count / len(values)
        return empty_ratio >= 0.8

    def rotate_agent(self) -> None:
        """Force user-agent rotation"""
        self.agent.rotate()

    def get_current_agent(self) -> str:
        """Get current user-agent string"""
        return self.agent.get_random_agent()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_scrape(
    url: str,
    schema: Type[BaseModel],
    model: str = "Qwen/Qwen2.5-7B-Instruct-1M",
    **kwargs
) -> BaseModel:
    """
    Quick one-off scraping without creating Scraparoni instance

    Args:
        url: Target URL
        schema: Pydantic extraction schema
        model: Model name
        **kwargs: Additional Scraparoni.scrape() arguments

    Returns:
        Extracted data
    """
    scraparoni = Scraparoni(model_name=model)
    return scraparoni.scrape(url, schema, **kwargs)
