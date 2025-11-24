from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Any, Set, Optional
from urllib.parse import urlparse

class ElementAnalyzer:
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'lxml')

    def find_potential_interactive_elements(self, current_url: str = "") -> List[Dict[str, Any]]:
        elements = []
        seen_items = set() 
        current_domain = urlparse(current_url).netloc if current_url else ""

        # --- 1. HOVER CANDIDATES ---
        nav_candidates = self.soup.find_all(['nav', 'header'])
        for div in self.soup.find_all(['div', 'ul']):
            classes = str(div.get('class', [])).lower()
            if 'menu' in classes or 'nav' in classes:
                nav_candidates.append(div)

        for container in nav_candidates:
            for el in container.find_all(['a', 'span', 'li', 'button']):
                text = self._clean_text(el)
                href = el.get('href', '')
                
                if not text or len(text) < 2: continue
                unique_key = (text, href)
                if unique_key in seen_items: continue
                
                elements.append({"text": text, "tag": el.name, "type": "nav", "href": href})
                seen_items.add(unique_key)

        # --- 2. POPUP CANDIDATES ---
        all_interactives = self.soup.find_all(['a', 'button', 'input'])
        
        for el in all_interactives:
            if el.name == 'input' and el.get('type') not in ['submit', 'button']: continue

            text = self._clean_text(el)
            href = el.get('href', '')
            unique_key = (text, href)

            if not text: continue
            if unique_key in seen_items: continue
            if len(text) > 60: continue 

            noise = ["skip to", "video unavailable", "loading", "advertisement"]
            if any(w in text.lower() for w in noise): continue

            elements.append({
                "text": text, 
                "tag": el.name, 
                "type": "trigger", 
                "href": href
            })
            seen_items.add(unique_key)

        return elements

    def _clean_text(self, el):
        return ' '.join(el.get_text(separator=' ', strip=True).split())

    @staticmethod
    def compare_doms(initial_visible_texts: Set[str], final_html: str) -> List[Dict[str, Any]]:
        """
        Identifies links in the final HTML that were NOT visible initially.
        Uses the 'Visible Text' set from BrowserManager for accuracy.
        """
        final_soup = BeautifulSoup(final_html, 'lxml')
        new_elements = []

        IGNORE = ["video", "supported", "unavailable", "loading", "advertisement"]

        for tag in final_soup.find_all('a', href=True):
            raw_text = tag.get_text(separator=' ', strip=True)
            text = ' '.join(raw_text.split())
            
            if not text: continue
            if any(x in text.lower() for x in IGNORE): continue

            # CRITICAL CHECK: Was this text visible before?
            # We assume if the text wasn't in the initial visible set, it's new.
            if text not in initial_visible_texts:
                new_elements.append({
                    "text": text, 
                    "tag": "a", 
                    "href": tag['href']
                })
        return new_elements

    @staticmethod
    def analyze_modal_dialog(initial_html: str, final_html: str) -> Dict[str, Any] | None:
        initial_soup = BeautifulSoup(initial_html, 'lxml')
        final_soup = BeautifulSoup(final_html, 'lxml')
        initial_text_blob = initial_soup.get_text()
        
        candidates = final_soup.select("div[role='dialog'], div[class*='modal'], div[class*='popup'], aside")
        if not candidates:
            candidates = final_soup.find_all('div')

        for cand in candidates:
            text = cand.get_text(separator=' ', strip=True)
            if not text or len(text) < 15: continue
            if "video" in text.lower(): continue 

            if text not in initial_text_blob:
                btns = cand.find_all(['button', 'a'])
                safe_buttons = []
                for b in btns:
                    t = b.get_text(strip=True)
                    if t: safe_buttons.append({"text": t})
                
                btn_str = ' '.join([b['text'].lower() for b in safe_buttons])
                
                if any(x in btn_str for x in ['cancel', 'close', 'ok', 'continue', 'stay', 'leave', 'yes', 'no']):
                    
                    title_el = cand.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
                    if title_el:
                        final_title = title_el.get_text(strip=True)
                    else:
                        raw_text = cand.get_text(separator=' ', strip=True)
                        for btn in safe_buttons:
                            raw_text = raw_text.replace(btn['text'], "")
                        final_title = ' '.join(raw_text.split())
                        if len(final_title) > 80: final_title = final_title[:80] + "..."

                    return {
                        "title": final_title,
                        "buttons": safe_buttons
                    }
        return None