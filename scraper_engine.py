"""
Scraper Engine for OmegaSports Headless Simulation

Uses Playwright with system Chromium for JavaScript-rendered web scraping.
Falls back to requests/BeautifulSoup for simpler pages.
Returns clean Markdown content for data ingestion by Perplexity Agent.
"""

import asyncio
import logging
import os
import shutil
import re
from typing import Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

SYSTEM_CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser")

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)


def html_to_markdown(html: str) -> str:
    """Convert HTML to simple Markdown format."""
    soup = BeautifulSoup(html, 'lxml')
    
    for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
        script.decompose()
    
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        level = int(tag.name[1])
        tag.replace_with(f"\n{'#' * level} {tag.get_text().strip()}\n")
    
    for tag in soup.find_all('a'):
        href = tag.get('href', '')
        text = tag.get_text().strip()
        if href and text:
            tag.replace_with(f"[{text}]({href})")
    
    for tag in soup.find_all('li'):
        tag.replace_with(f"- {tag.get_text().strip()}\n")
    
    for tag in soup.find_all(['p', 'div']):
        text = tag.get_text().strip()
        if text:
            tag.replace_with(f"{text}\n\n")
    
    text = soup.get_text(separator='\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    return text.strip()


class OmegaScraper:
    """
    Web scraper optimized for sports data extraction.
    
    Features:
    - JavaScript rendering via Playwright with system Chromium
    - Fallback to requests for simple pages
    - Clean Markdown output
    """
    
    def __init__(self, headless: bool = True, verbose: bool = False):
        self.headless = headless
        self.verbose = verbose
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not installed. Using requests fallback.")
    
    async def fetch_with_playwright(self, url: str, wait_for: Optional[str] = None) -> dict:
        """Fetch URL using Playwright with system Chromium."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    executable_path=SYSTEM_CHROMIUM,
                    headless=self.headless,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-software-rasterizer',
                    ]
                )
                
                page = await browser.new_page()
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                if wait_for:
                    await page.wait_for_selector(wait_for, timeout=10000)
                
                content = await page.content()
                title = await page.title()
                
                await browser.close()
                
                markdown = html_to_markdown(content)
                
                return {
                    "success": True,
                    "markdown": markdown,
                    "url": url,
                    "fetched_at": datetime.now().isoformat(),
                    "title": title,
                    "method": "playwright"
                }
                
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return None
    
    def fetch_with_requests(self, url: str) -> dict:
        """Fallback fetch using requests."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            markdown = html_to_markdown(response.text)
            
            soup = BeautifulSoup(response.text, 'lxml')
            title = soup.title.string if soup.title else ""
            
            return {
                "success": True,
                "markdown": markdown,
                "url": url,
                "fetched_at": datetime.now().isoformat(),
                "title": title,
                "method": "requests"
            }
            
        except Exception as e:
            logger.error(f"Requests error for {url}: {e}")
            return {
                "success": False,
                "markdown": "",
                "url": url,
                "fetched_at": datetime.now().isoformat(),
                "error": str(e),
                "method": "requests"
            }
    
    async def fetch_sports_markdown(self, url: str, wait_for: Optional[str] = None) -> dict:
        """
        Fetch a URL and return content as clean Markdown.
        
        Uses Playwright with system Chromium for JS-rendered pages,
        falls back to requests for simpler pages.
        """
        if PLAYWRIGHT_AVAILABLE and SYSTEM_CHROMIUM:
            result = await self.fetch_with_playwright(url, wait_for)
            if result:
                return result
        
        return self.fetch_with_requests(url)
    
    async def fetch_multiple(self, urls: list) -> list:
        """Fetch multiple URLs."""
        tasks = [self.fetch_sports_markdown(url) for url in urls]
        return await asyncio.gather(*tasks)


def fetch_sports_markdown(url: str, wait_for: Optional[str] = None) -> dict:
    """
    Synchronous wrapper for fetching sports data as Markdown.
    
    This is the main entry point for Perplexity Agent to call.
    
    Example:
        >>> result = fetch_sports_markdown("https://www.espn.com/nba/schedule")
        >>> if result["success"]:
        ...     print(result["markdown"][:500])
    """
    scraper = OmegaScraper()
    return asyncio.run(scraper.fetch_sports_markdown(url, wait_for))


def fetch_multiple_urls(urls: list) -> list:
    """Synchronous wrapper for fetching multiple URLs."""
    scraper = OmegaScraper()
    return asyncio.run(scraper.fetch_multiple(urls))


def parse_to_game_data(
    markdown: str,
    sport: str = "NBA",
    home_team: str = "",
    away_team: str = "",
    source_url: str = ""
) -> dict:
    """
    Parse scraped markdown into GameData schema format.
    
    This is a helper function for Perplexity to validate data before simulation.
    The agent should extract betting lines from markdown and fill in the structure.
    
    Args:
        markdown: Raw scraped markdown content
        sport: Sport identifier (NBA, NFL, etc.)
        home_team: Home team name
        away_team: Away team name
        source_url: Source URL of the scraped content
    
    Returns:
        dict matching GameData schema structure (for Perplexity to fill)
    
    Example:
        >>> result = fetch_sports_markdown("https://www.espn.com/nba/game")
        >>> template = parse_to_game_data(
        ...     result["markdown"],
        ...     sport="NBA",
        ...     home_team="Boston Celtics",
        ...     away_team="Indiana Pacers"
        ... )
        >>> # Perplexity agent should now fill in the betting lines
    """
    try:
        from omega.schema import GameData, BettingLine, PropBet
        
        game_template = GameData(
            sport=sport,
            league=sport,
            home_team=home_team,
            away_team=away_team,
            raw_markdown_source=markdown[:5000] if markdown else None,
            source_url=source_url,
            moneyline=None,
            spread=None,
            total=None,
            player_props=[]
        )
        
        return game_template.model_dump()
        
    except ImportError:
        return {
            "sport": sport,
            "league": sport,
            "home_team": home_team,
            "away_team": away_team,
            "raw_markdown_source": markdown[:5000] if markdown else None,
            "source_url": source_url,
            "moneyline": None,
            "spread": None,
            "total": None,
            "player_props": [],
            "_note": "omega.schema not available - using dict fallback"
        }


def validate_game_data(data: dict) -> tuple:
    """
    Validate a dict against the GameData schema.
    
    Args:
        data: Dictionary with game data
    
    Returns:
        Tuple of (is_valid: bool, validated_data_or_errors: dict/list)
    
    Example:
        >>> is_valid, result = validate_game_data({
        ...     "sport": "NBA",
        ...     "league": "NBA",
        ...     "home_team": "Celtics",
        ...     "away_team": "Pacers"
        ... })
    """
    try:
        from omega.schema import GameData
        validated = GameData(**data)
        return True, validated.model_dump()
    except ImportError:
        return True, data
    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("OmegaSports Scraper Engine - Test Mode")
    print("=" * 60)
    print(f"System Chromium: {SYSTEM_CHROMIUM or 'Not found'}")
    print(f"Playwright available: {PLAYWRIGHT_AVAILABLE}")
    
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.espn.com/nba/schedule"
    
    print(f"\nTest URL: {test_url}")
    print("-" * 60)
    
    result = fetch_sports_markdown(test_url)
    
    if result["success"]:
        print(f"[SUCCESS] Method: {result.get('method', 'unknown')}")
        print(f"Fetched at: {result['fetched_at']}")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Markdown length: {len(result['markdown'])} characters")
        print("\n--- First 1500 chars of Markdown ---\n")
        print(result["markdown"][:1500])
        print("\n--- End Preview ---")
    else:
        print(f"[FAILED] Error: {result.get('error', 'Unknown')}")
    
    print("=" * 60)
