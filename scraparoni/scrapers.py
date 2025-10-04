"""
Scraparoni - Web Scraping Engines
Dual-mode scraping: Lightning-fast curl-cffi & powerful Playwright
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from .agents import ScraparoniAgent


class BaseScraper(ABC):
    """Abstract base scraper for all Scraparoni scrapers"""

    def __init__(self, agent: Optional[ScraparoniAgent] = None):
        """
        Initialize base scraper

        Args:
            agent: ScraparoniAgent instance for user-agent rotation
        """
        self.agent = agent or ScraparoniAgent()

    @abstractmethod
    def fetch(self, url: str, **kwargs) -> str:
        """Fetch HTML content from URL"""
        pass


class PhantomScraper(BaseScraper):
    """
    Lightning-fast scraper using curl-cffi with TLS fingerprint impersonation
    Bypasses Cloudflare, DataDome, and most anti-bot systems
    """

    IMPERSONATE_PROFILES = [
        "chrome120",
        "chrome119",
        "chrome110",
        "edge101",
        "safari15_5",
        "safari15_3",
    ]

    def __init__(
        self,
        agent: Optional[ScraparoniAgent] = None,
        impersonate: str = "chrome120",
        proxy: Optional[str] = None,
        verify_ssl: bool = True,
    ):
        """
        Initialize PhantomScraper

        Args:
            agent: ScraparoniAgent instance
            impersonate: Browser to impersonate (chrome120, safari15_5, etc.)
            proxy: Proxy URL (http://user:pass@host:port)
            verify_ssl: Verify SSL certificates
        """
        super().__init__(agent)
        self.impersonate = impersonate
        self.proxy = proxy
        self.verify_ssl = verify_ssl

    def fetch(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        **kwargs
    ) -> str:
        """
        Fetch HTML using curl-cffi with TLS fingerprint impersonation

        Args:
            url: Target URL
            method: HTTP method (GET, POST, etc.)
            data: Request body data
            headers: Additional headers
            timeout: Request timeout in seconds
            **kwargs: Additional curl-cffi arguments

        Returns:
            HTML content as string

        Raises:
            Exception: If request fails
        """
        # Lazy import to speed up module loading
        from curl_cffi import requests

        # Merge headers with agent headers
        request_headers = self.agent.get_headers(headers)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                data=data,
                impersonate=self.impersonate,
                timeout=timeout,
                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                verify=self.verify_ssl,
                **kwargs
            )
            response.raise_for_status()
            return response.text

        except Exception as e:
            raise Exception(f"PhantomScraper failed for {url}: {str(e)}")


class BrowserScraper(BaseScraper):
    """
    Full-power browser automation using Playwright
    Handles JavaScript-heavy SPAs, dynamic content, and complex interactions
    """

    def __init__(
        self,
        agent: Optional[ScraparoniAgent] = None,
        headless: bool = True,
        browser_type: str = "chromium",
        proxy: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize BrowserScraper

        Args:
            agent: ScraparoniAgent instance
            headless: Run browser in headless mode
            browser_type: Browser engine (chromium, firefox, webkit)
            proxy: Proxy config dict {"server": "http://host:port", "username": "...", "password": "..."}
        """
        super().__init__(agent)
        self.headless = headless
        self.browser_type = browser_type
        self.proxy = proxy
        self._playwright = None
        self._browser = None

    def __enter__(self):
        """Context manager entry"""
        # Lazy import to speed up module loading
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        browser_launcher = getattr(self._playwright, self.browser_type)

        launch_options = {"headless": self.headless}
        if self.proxy:
            launch_options["proxy"] = self.proxy

        self._browser = browser_launcher.launch(**launch_options)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def fetch(
        self,
        url: str,
        wait_for: Optional[str] = None,
        wait_time: int = 3500,
        execute_script: Optional[str] = None,
        screenshot: Optional[str] = None,
        wait_until: str = "domcontentloaded",
        **kwargs
    ) -> str:
        """
        Fetch HTML using Playwright with full JavaScript execution

        Args:
            url: Target URL
            wait_for: CSS selector to wait for before extracting content
            wait_time: Time to wait in milliseconds after page load (default: 3500)
            execute_script: JavaScript to execute before extraction
            screenshot: Path to save screenshot (optional)
            wait_until: Page load strategy - 'load', 'domcontentloaded', 'networkidle', 'commit' (default: domcontentloaded)
            **kwargs: Additional page.goto() options

        Returns:
            HTML content as string

        Raises:
            RuntimeError: If not used as context manager
            Exception: If scraping fails
        """
        if not self._browser:
            raise RuntimeError("BrowserScraper must be used as context manager: 'with BrowserScraper() as scraper:'")

        try:
            # Create browser context with fingerprint (disable cache for fresh content)
            context = self._browser.new_context(
                user_agent=self.agent.get_random_agent(),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation"],
                bypass_csp=True,
                ignore_https_errors=False,
            )

            page = context.new_page()

            # Navigate to URL - use domcontentloaded by default (more reliable)
            # Also disable cache to ensure fresh content
            goto_options = {
                "wait_until": wait_until,
                "timeout": 60000,
            }
            goto_options.update(kwargs)

            try:
                page.goto(url, **goto_options)
            except Exception as e:
                # If networkidle fails, retry with domcontentloaded
                if wait_until == "networkidle":
                    print(f"⚠️  networkidle timeout, retrying with domcontentloaded...")
                    goto_options["wait_until"] = "domcontentloaded"
                    page.goto(url, **goto_options)
                else:
                    raise e

            # Wait for specific selector or additional time for JS to render
            if wait_for:
                page.wait_for_selector(wait_for, timeout=wait_time + 5000)
            else:
                page.wait_for_timeout(wait_time)

            # Execute custom JavaScript if provided
            if execute_script:
                page.evaluate(execute_script)
                page.wait_for_timeout(500)  # Let JS settle

            # Take screenshot if requested
            if screenshot:
                page.screenshot(path=screenshot, full_page=True)

            # Extract content
            content = page.content()
            context.close()

            return content

        except Exception as e:
            raise Exception(f"BrowserScraper failed for {url}: {str(e)}")

    def fetch_with_interaction(
        self,
        url: str,
        interactions: list[Dict[str, Any]],
        wait_time: int = 1000,
    ) -> str:
        """
        Fetch with custom interactions (clicks, scrolls, inputs)

        Args:
            url: Target URL
            interactions: List of interaction dicts
                Examples:
                {"action": "click", "selector": ".button"}
                {"action": "fill", "selector": "#input", "value": "text"}
                {"action": "scroll", "direction": "down", "times": 3}
                {"action": "wait", "ms": 2000}
            wait_time: Wait between interactions (ms)

        Returns:
            HTML content after interactions
        """
        if not self._browser:
            raise RuntimeError("BrowserScraper must be used as context manager")

        try:
            context = self._browser.new_context(
                user_agent=self.agent.get_random_agent(),
                viewport={"width": 1920, "height": 1080},
            )

            page = context.new_page()
            page.goto(url, wait_until="networkidle")

            # Execute interactions
            for interaction in interactions:
                action = interaction.get("action")

                if action == "click":
                    page.click(interaction["selector"])
                elif action == "fill":
                    page.fill(interaction["selector"], interaction["value"])
                elif action == "scroll":
                    direction = interaction.get("direction", "down")
                    times = interaction.get("times", 1)
                    for _ in range(times):
                        page.evaluate(f"window.scrollBy(0, {1000 if direction == 'down' else -1000})")
                        page.wait_for_timeout(300)
                elif action == "wait":
                    page.wait_for_timeout(interaction.get("ms", 1000))

                page.wait_for_timeout(wait_time)

            content = page.content()
            context.close()

            return content

        except Exception as e:
            raise Exception(f"BrowserScraper interaction failed: {str(e)}")
