# 🍝 Scraparoni

**Advanced LLM-Powered Web Scraper**

Scraparoni combines lightning-fast HTTP scraping with full browser automation, dynamic user-agent rotation, and intelligent LLM-based data extraction.

## ✨ Features

- **🚀 Dual Scraping Engines**
  - **PhantomScraper**: Ultra-fast curl-cffi with TLS fingerprinting (bypasses Cloudflare, DataDome)
  - **BrowserScraper**: Full Playwright automation for JavaScript-heavy sites

- **🧠 LLM-Powered Extraction**
  - Local LLM (Qwen2.5-7B) extracts structured data from raw HTML
  - Returns validated Pydantic models with `.json()`, `.dict()`, `.model()` methods
  - JSON output with proper double-quote formatting
  - Smart chunking for large HTML files (15k chunks with keyword-based relevance scoring)

- **🎭 Dynamic User-Agent Rotation**
  - 21 realistic browser fingerprints (14 desktop & 7 mobile)
  - Complete HTTP headers with security flags
  - Sticky or rotating mode

- **🔄 Auto-Fallback**
  - Automatically detects JavaScript-rendered content
  - Falls back from fast scraping to browser when needed
  - Finds chunks with most complete data

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
playwright install chromium  # For BrowserScraper
```

### Basic Usage

```python
from scraparoni import Scraparoni as scrapey
from pydantic import BaseModel, Field
from typing import Optional, List

class NavbarItems(BaseModel):
    navbar_items: List[str] = Field(description="The navbar items")


scrapey = scrapey()
result = scrapey.scrape(
    url="https://www.scrapethissite.com/",
    schema=NavbarItems,
    use_browser=False,
    instructions="Give me the names of the items in the navbar"
)

print(result.json())
```

### Real-World Example

```python
from scraparoni import Scraparoni
from pydantic import BaseModel, Field

class MMR(BaseModel):
    ones_mmr: int = Field(description="The mmr for 1v1")
    twos_mmr: int = Field(description="The mmr for 2v2")
    threes_mmr: int = Field(description="The mmr for 3v3")

scraper = Scraparoni()
result = scraper.scrape(
    url="https://rocketleague.tracker.network/rocket-league/profile/epic/zenrll/overview",
    schema=MMR,
    use_browser=True,
    save_html="debug.html",  # Save HTML for debugging
    instructions="Get mmr for 1v1, 2v2, 3v3"
)

print(result.json())
```

## 📚 Usage Examples

### 1. Fast Scraping (PhantomScraper)

```python
from pydantic import BaseModel, Field
from scraparoni import Scraparoni

class Story(BaseModel):
    title: str = Field(description="Story title")
    points: int = Field(description="Story points")

scraper = Scraparoni()

result = scraper.scrape_with_phantom(
    url="https://news.ycombinator.com",
    schema=Story,
    instructions="Extract the top story"
)

print(result.json())
```

### 2. Browser Automation (JavaScript Sites)

```python
from pydantic import BaseModel, Field
from typing import List
from scraparoni import Scraparoni

class GameOdds(BaseModel):
    team1: str = Field(description="First team name")
    team2: str = Field(description="Second team name")
    team1_odds: int = Field(description="Moneyline for team 1")
    team2_odds: int = Field(description="Moneyline for team 2")

class AllGames(BaseModel):
    games: List[GameOdds] = Field(description="All games and odds")

scraper = Scraparoni()

result = scraper.scrape_with_browser(
    url="https://sportsbook.example.com",
    schema=AllGames,
    wait_for=".odds-container",  # Wait for element
    headless=True
)
```

## 🏗️ Architecture

```
scraparoni/
├── __init__.py         # Package exports
├── core.py             # Scraparoni main orchestrator
├── scrapers.py         # PhantomScraper & BrowserScraper
├── extractor.py        # Weaver (LLM extraction with smart chunking)
└── agents.py           # ScraperoniAgent (user-agent rotation)
```

### Components

- **Scraparoni**: Main class that orchestrates all components
- **PhantomScraper**: Fast curl-cffi scraper with TLS impersonation
- **BrowserScraper**: Playwright-based browser automation
- **Weaver**: LLM extraction engine with smart chunking (tries chunks with >0.4 relevance, keeps best result)
- **ScraperoniAgent**: Dynamic user-agent rotation system
- **ScraperoniResponse**: Wrapper providing `.json()`, `.dict()`, `.model()` methods

## 🎨 Creating Schemas

Scraparoni uses Pydantic models to define what data to extract. Simply create a class with typed fields:

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class Product(BaseModel):
    title: str = Field(description="Product title")
    price: Optional[str] = Field(None, description="Product price in USD")
    rating: Optional[float] = Field(None, description="Average rating out of 5")
    features: Optional[List[str]] = Field(None, description="Key product features")

class Article(BaseModel):
    headline: str = Field(description="Article headline")
    author: Optional[str] = Field(None, description="Author name")
    content: str = Field(description="Full article text")
    tags: Optional[List[str]] = Field(None, description="Article tags")
```

**Pro tip**: The `description` field helps the LLM understand what to extract. Be specific!

## ⚙️ Advanced Configuration

### Custom Model

```python
scraper = Scraparoni(
    model_name="Qwen/Qwen2.5-14B-Instruct",  # Use larger model
    prefer_desktop=True,
    sticky_agent=False,  # Rotate user-agent each request
    verbose=True  # Show detailed loading progress
)
```

### Direct Scraper Access

```python
from scraparoni import PhantomScraper, ScraperoniAgent

agent = ScraperoniAgent(prefer_desktop=False)  # Mobile agents
phantom = PhantomScraper(
    agent=agent,
    impersonate="safari15_5",
    proxy="http://proxy:8080"
)

html = phantom.fetch("https://example.com")
```

### Browser Configuration

```python
from scraparoni import BrowserScraper, ScraperoniAgent

agent = ScraperoniAgent()
with BrowserScraper(agent=agent, headless=False, browser_type="firefox") as browser:
    html = browser.fetch(
        "https://example.com",
        wait_for=".content",
        wait_time=5000,
        screenshot="/tmp/page.png"
    )
```

## 🔧 API Reference

### Scraparoni Methods

- `scrape(url, schema, instructions, use_browser, auto_fallback, save_html, **kwargs)` - Auto-select scraper with fallback
- `scrape_with_phantom(url, schema, instructions, **kwargs)` - Use PhantomScraper (fast)
- `scrape_with_browser(url, schema, instructions, wait_for, headless, **kwargs)` - Use BrowserScraper (JS support)
- `scrape_with_interaction(url, schema, interactions, instructions, headless)` - Interactive scraping
- `scrape_many(urls, schema, instructions, use_browser, **kwargs)` - Batch scraping
- `fetch_html(url, use_browser, **kwargs)` - Fetch raw HTML without extraction
- `extract_from_html(html, schema, instructions)` - Extract from pre-fetched HTML
- `analyze_html(html, prompt, temperature)` - Custom analysis without schema
- `rotate_agent()` - Force user-agent rotation
- `get_current_agent()` - Get current user-agent string

### PhantomScraper

- `fetch(url, method, data, headers, timeout, **kwargs)` - Fetch with curl-cffi

### BrowserScraper

- `fetch(url, wait_for, wait_time, execute_script, screenshot, wait_until, **kwargs)` - Fetch with Playwright
- `fetch_with_interaction(url, interactions, wait_time)` - Fetch with user interactions

### Weaver

- `extract(html_content, schema, instructions, max_length, temperature, max_tokens, smart_chunking)` - Extract structured data
- `extract_batch(html_contents, schema, instructions, **kwargs)` - Batch extraction
- `custom_prompt(html_content, prompt, temperature, max_tokens)` - Custom prompt without schema

### ScraperoniResponse

- `json(indent=2)` - Return formatted JSON string with double quotes
- `dict()` - Return Python dictionary
- `model()` - Return raw Pydantic model

## 🧠 How Smart Chunking Works

For large HTML files (>15k chars), Scraparoni:

1. Splits HTML into 15k character chunks with 1k overlap
2. Extracts keywords from your Pydantic schema descriptions
3. Scores each chunk by keyword density
4. Tries all chunks with relevance score > 0.4
5. Returns the result with the most complete data

This ensures accurate extraction even from massive pages while staying within LLM context limits.

## 📝 License

MIT

## 🤝 Contributing

Contributions welcome! This is a tool for defensive security research and ethical web scraping only.

---

**Made with 🍝 by the Scraparoni team**
