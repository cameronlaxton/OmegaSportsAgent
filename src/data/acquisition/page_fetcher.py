"""
Page fetcher — retrieves and extracts text content from web URLs.

Used after web search returns URLs that need their content extracted
for the LLM extraction stage.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("omega.data.acquisition.page_fetcher")

# Max content length to prevent processing enormous pages
_MAX_CONTENT_LENGTH = 100_000  # 100KB of text


def fetch_page_text(url: str, timeout: float = 10.0) -> Optional[str]:
    """Fetch a URL and return cleaned text content.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Cleaned text content, or None if fetch fails.
    """
    if not url or url.startswith("perplexity://"):
        return None

    try:
        import httpx

        resp = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; OmegaSportsAgent/1.0; "
                    "+https://github.com/omega-sports)"
                ),
            },
        )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "text/html" in content_type:
            return _html_to_text(resp.text)
        elif "text/plain" in content_type or "application/json" in content_type:
            return resp.text[:_MAX_CONTENT_LENGTH]
        else:
            logger.debug("Unsupported content type for %s: %s", url, content_type)
            return None

    except Exception as exc:
        logger.debug("Page fetch failed for %s: %s", url, exc)
        return None


def _html_to_text(html: str) -> str:
    """Convert HTML to clean text.

    Uses trafilatura if available (best quality), falls back to
    simple regex-based tag stripping.
    """
    try:
        import trafilatura
        text = trafilatura.extract(html, include_tables=True, include_links=False)
        if text:
            return text[:_MAX_CONTENT_LENGTH]
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: simple regex-based extraction
    return _simple_html_strip(html)


def _simple_html_strip(html: str) -> str:
    """Minimal HTML → text extraction using regex.

    Not as good as trafilatura but works without dependencies.
    """
    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)

    # Replace block-level tags with newlines
    text = re.sub(r"<(?:br|p|div|h[1-6]|li|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode common HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")

    # Clean up whitespace
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()

    return text[:_MAX_CONTENT_LENGTH]
