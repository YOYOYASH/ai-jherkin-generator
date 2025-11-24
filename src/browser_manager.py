import asyncio
from playwright.async_api import async_playwright, Page, Browser, Playwright
from typing import List, Dict, Optional
from urllib.parse import urlparse
from . import config

class BrowserManager:
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=config.BROWSER_ARGS
        )
        context = await self.browser.new_context(
            viewport={"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
            user_agent=config.USER_AGENT
        )
        self.page = await context.new_page()

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def go_to(self, url: str):
        if not self.page: return
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
        except Exception:
            pass

    async def scroll_to_bottom(self):
        if not self.page: return
        try:
            last_height = await self.page.evaluate("document.body.scrollHeight")
            while True:
                await self.page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(0.5)
                new_height = await self.page.evaluate("document.body.scrollHeight")
                current_scroll = await self.page.evaluate("window.scrollY + window.innerHeight")
                if current_scroll >= new_height:
                    break
                last_height = new_height
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
        except Exception:
            pass

    async def get_page_content(self) -> str:
        if not self.page: return ""
        try:
            return await self.page.content()
        except Exception:
            return ""

    async def get_visible_text_set(self) -> set:
        """
        Returns a set of all visible strings on the page.
        Crucial for detecting menus that are in DOM but hidden by CSS.
        """
        if not self.page: return set()
        try:
            # innerText only returns visible text
            full_text = await self.page.evaluate("document.body.innerText")
            # Split by lines and clean up
            return set(line.strip() for line in full_text.split('\n') if line.strip())
        except Exception:
            return set()

    async def is_element_visible(self, element_data: Dict) -> bool:
        if not self.page: return False
        text = element_data.get('text', '')
        href = element_data.get('href', '')

        try:
            if href:
                safe_href = href.replace('"', '\\"')
                loc = self.page.locator(f"a[href=\"{safe_href}\"]").first
                if await loc.count() > 0:
                    return await loc.is_visible()

            loc = self.page.get_by_text(text, exact=True).first
            if await loc.count() > 0:
                return await loc.is_visible()
            
            return False
        except Exception:
            return False

    async def hover_and_get_changes(self, element_data: Dict) -> Dict:
        if not self.page: raise ConnectionError("Browser not started")
        
        # Capture VISIBLE text before hover
        initial_visible = await self.get_visible_text_set()
        initial_content = await self.get_page_content()
        
        text = element_data.get("text")
        href = element_data.get("href")

        try:
            loc = None
            if href:
                 safe_href = href.replace('"', '\\"')
                 loc = self.page.locator(f"a[href=\"{safe_href}\"]").first
            
            if not loc or await loc.count() == 0:
                loc = self.page.get_by_text(text, exact=True).first

            if await loc.count() and await loc.is_visible():
                await loc.scroll_into_view_if_needed()
                await loc.hover(force=True)
                await asyncio.sleep(1.0) # Wait for animation
        except Exception:
            pass

        final_content = await self.get_page_content()
        
        # Capture DOM changes for link analysis
        return {
            "initial": initial_content, 
            "final": final_content,
            "initial_visible": initial_visible # Pass this specifically for diffing
        }

    async def click_and_get_changes(self, element_data: Dict) -> Dict:
        if not self.page: raise ConnectionError("Browser not started")

        initial_content = await self.get_page_content()
        initial_url = self.page.url
        text = element_data.get("text")
        href = element_data.get("href")

        try:
            loc = None
            if href:
                safe_href = href.replace('"', '\\"')
                loc = self.page.locator(f"a[href=\"{safe_href}\"]").first
            
            if not loc or await loc.count() == 0:
                loc = self.page.get_by_text(text, exact=True).first
                if await loc.count() == 0:
                     loc = self.page.get_by_role("button", name=text).first

            if loc and await loc.count() > 0:
                await loc.scroll_into_view_if_needed()
                await loc.click(timeout=2000, force=True)
                await asyncio.sleep(2.0)
        except Exception:
            pass

        final_url = self.page.url
        final_content = await self.get_page_content()
        
        is_navigated = urlparse(initial_url).netloc != urlparse(final_url).netloc
        
        return {
            "initial": initial_content,
            "final": final_content,
            "navigated": is_navigated
        }