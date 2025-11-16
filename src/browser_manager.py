import asyncio
from playwright.async_api import async_playwright, Page, Browser, Playwright, TimeoutError as PlaywrightTimeout
from typing import List, Dict, Optional
from urllib.parse import urlparse
from . import config

class BrowserManager:
    """
    Manages browser interactions using Playwright.
    """
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def start(self):
        """
        Starts the playwright browser instance.
        """
        self.playwright = await async_playwright().start()
        # Launch with args to avoid some common issues
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
        """
        Closes the playwright browser instance.
        """
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _handle_cookie_banner(self):
        if not self.page:
            return

        for selector in config.COOKIE_SELECTORS:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible(timeout=500):
                    await element.click(timeout=800)
                    print(f"  ℹ Dismissed cookie banner using: {selector}")
                    await self.page.wait_for_timeout(500)
                    return
            except Exception:
                continue

        # Don't block if no selector works
        return


    async def go_to(self, url: str):
        """
        Navigates to a specific URL and handles common blockers like cookie banners.
        """
        self.cookie_dismissed = getattr(self, "cookie_dismissed", False)
        if not self.page:
            raise ConnectionError("Browser is not started.")
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=config.BROWSER_TIMEOUT)
            await self.page.wait_for_timeout(config.PAGE_LOAD_WAIT)
            if not self.cookie_dismissed:
                await self._handle_cookie_banner()
                self.cookie_dismissed = True
            await self.page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            raise

    async def get_page_content(self) -> str:
        """
        Returns the HTML content of the current page.
        Retries if page is navigating.
        """
        if not self.page:
            raise ConnectionError("Browser is not started.")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
                return await self.page.content()
            except PlaywrightTimeout:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
                raise
            except Exception as e:
                if "navigating" in str(e).lower() and attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise

    async def get_element_states(self, selector: str) -> List[Dict]:
        """
        Gets the state of all elements matching a selector.
        """
        if not self.page:
            raise ConnectionError("Browser is not started.")
        elements = await self.page.query_selector_all(selector)
        states = []
        for element in elements:
            try:
                box = await element.bounding_box()
                is_visible = await element.is_visible()
                states.append({
                    "selector": selector,
                    "visible": is_visible,
                    "box": box,
                    "text": await element.text_content()
                })
            except Exception:
                continue
        return states

    async def hover_and_get_changes(self, element_data: Dict) -> Dict:
        """
        Hovers over an element identified by its text and captures the DOM state.
        """
        if not self.page:
            raise ConnectionError("Browser is not started.")

        initial_content = await self.get_page_content()
        element_text = element_data.get("text")
        if not element_text:
            return {"initial": initial_content, "final": initial_content}

        try:
            # Try multiple strategies to find and hover over the element
            element = None
            # Strategy 1: Exact text match
            try:
                element = self.page.get_by_text(element_text, exact=True).first
                await element.scroll_into_view_if_needed()
                await element.hover(timeout=3000)
            except Exception:
                # Strategy 2: Partial text match
                try:
                    element = self.page.get_by_text(element_text, exact=False).first
                    await element.scroll_into_view_if_needed()
                    await element.hover(timeout=3000)
                except Exception:
                    # Strategy 3: Use role-based selectors
                    try:
                        element = self.page.get_by_role("link", name=element_text).first
                        await element.scroll_into_view_if_needed()
                        await element.hover(timeout=3000)
                    except Exception:
                        try:
                            element = self.page.get_by_role("button", name=element_text).first
                            await element.scroll_into_view_if_needed()
                            await element.hover(timeout=3000)
                        except Exception:
                            print(f"Could not find element with text '{element_text}' using any strategy")
                            return {"initial": initial_content, "final": initial_content}

            # Wait for animations / network activity after hover
            try:
                await self.page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                # Not fatal; some sites won't hit network after hover
                pass

            await self.page.wait_for_timeout(800)

        except Exception as e:
            print(f"Error during hover on element with text '{element_text}': {e}")
            return {"initial": initial_content, "final": initial_content}

        final_content = await self.get_page_content()
        return {"initial": initial_content, "final": final_content}

    async def click_and_get_changes(self, element_data: Dict) -> Dict:
        """
        Clicks an element identified by its text and captures the DOM state.
        Handles both modals and navigation. Now allows internal links for testing.
        """
        if not self.page:
            raise ConnectionError("Browser is not started.")

        initial_content = await self.get_page_content()
        initial_url = self.page.url
        element_text = element_data.get("text")

        try:
            element = None
            clicked = False

            # Strategy 1: Exact text match
            try:
                element = self.page.get_by_text(element_text, exact=True).first
                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                href = None
                if tag_name == 'a':
                    href = await element.get_attribute('href')
                # Only skip if link is external (different domain)
                if href:
                    parsed = urlparse(href)
                    if parsed.netloc and parsed.netloc != urlparse(initial_url).netloc:
                        print(f"  → Skipping external navigation link (href: {href})")
                        return {
                            "initial": initial_content,
                            "final": initial_content,
                            "initial_url": initial_url,
                            "final_url": initial_url,
                            "skipped": True
                        }

                await element.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)
                await element.click(timeout=4000, no_wait_after=True)
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=3000)
                except:
                    pass

                clicked = True
            except Exception:
                # Strategy 2: Partial text match
                try:
                    element = self.page.get_by_text(element_text, exact=False).first
                    await element.scroll_into_view_if_needed()
                    href = None
                    try:
                        href = await element.get_attribute('href')
                    except Exception:
                        href = None
                    if href:
                        parsed = urlparse(href)
                        if parsed.netloc and parsed.netloc != urlparse(initial_url).netloc:
                            print(f"  → Skipping external navigation link (href: {href})")
                            return {
                                "initial": initial_content,
                                "final": initial_content,
                                "initial_url": initial_url,
                                "final_url": initial_url,
                                "skipped": True
                            }
                    await element.click(timeout=4000, no_wait_after=True)
                    clicked = True
                except Exception:
                    # Strategy 3: Role-based selectors
                    try:
                        element = self.page.get_by_role("button", name=element_text).first
                        await element.scroll_into_view_if_needed()
                        await element.click(timeout=4000, no_wait_after=True)
                        clicked = True
                    except Exception:
                        try:
                            element = self.page.get_by_role("link", name=element_text).first
                            await element.scroll_into_view_if_needed()
                            href = await element.get_attribute('href')
                            if href:
                                parsed = urlparse(href)
                                if parsed.netloc and parsed.netloc != urlparse(initial_url).netloc:
                                    print(f"  → Skipping external navigation link (href: {href})")
                                    return {
                                        "initial": initial_content,
                                        "final": initial_content,
                                        "initial_url": initial_url,
                                        "final_url": initial_url,
                                        "skipped": True
                                    }
                            await element.click(timeout=4000, no_wait_after=True)
                            clicked = True
                        except Exception:
                            print(f"Could not find clickable element with text '{element_text}'")
                            return {
                                "initial": initial_content,
                                "final": initial_content,
                                "initial_url": initial_url,
                                "final_url": initial_url,
                            }

            if not clicked:
                return {
                    "initial": initial_content,
                    "final": initial_content,
                    "initial_url": initial_url,
                    "final_url": initial_url,
                }

            # Wait a bit for possible modal or DOM changes
            await asyncio.sleep(1.5)

            current_url = self.page.url
            if current_url != initial_url:
                print(f"  → Navigation detected: {initial_url} -> {current_url}")
                try:
                    final_content = await self.get_page_content()
                except Exception:
                    final_content = initial_content
                return {
                    "initial": initial_content,
                    "final": final_content,
                    "initial_url": initial_url,
                    "final_url": current_url,
                    "navigated": True
                }

        except Exception as e:
            print(f"Error clicking element with text '{element_text}': {e}")
            return {
                "initial": initial_content,
                "final": initial_content,
                "initial_url": initial_url,
                "final_url": initial_url,
            }

        try:
            final_content = await self.get_page_content()
            final_url = self.page.url
        except Exception as e:
            print(f"  → Could not get final content: {e}")
            return {
                "initial": initial_content,
                "final": initial_content,
                "initial_url": initial_url,
                "final_url": initial_url,
            }

        return {
            "initial": initial_content,
            "final": final_content,
            "initial_url": initial_url,
            "final_url": final_url,
        }


if __name__ == "__main__":
    import asyncio
    async def main():
        browser = BrowserManager()
        await browser.start()
        try:
            await browser.go_to("https://www.apple.com/in/")
            content = await browser.get_page_content()
            print("Initial page content length:", len(content))
        finally:
            await browser.close()
    asyncio.run(main())
