from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Any, Set

class ElementAnalyzer:
    """
    Analyzes HTML content to find interactive elements and differences in DOM structure.
    """

    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'lxml')

    def find_potential_interactive_elements(self) -> List[Dict[str, Any]]:
        """
        Finds elements that are likely to be interactive (hoverable or clickable).
        """
        interactive_elements = []
        selectors = [
            "nav a", "nav button", "nav li",
            "header a", "header button",
            "[role='button']", "[role='menuitem']",
            "a[href]", "button",
            "div[onclick]", "div[onmouseover]",
            "[class*='menu']", "[class*='nav']",
            "[class*='dropdown']", "[class*='link']"
        ]

        found_elements: Set[Tag] = set()

        for selector in selectors:
            try:
                elements = self.soup.select(selector)
            except Exception:
                elements = []
            for element in elements:
                if element not in found_elements:
                    found_elements.add(element)

        for element in found_elements:
            text = self._get_element_text(element)
            if text and len(text) < 200:
                interactive_elements.append({
                    "text": text,
                    "tag": element.name,
                    "classes": element.get('class', []),
                    "id": element.get('id', '')
                })

        # Fallback: if nothing found, try headings + nav
        if not interactive_elements:
            for el in self.soup.find_all(['a', 'button']):
                text = self._get_element_text(el)
                if text:
                    interactive_elements.append({
                        "text": text,
                        "tag": el.name,
                        "classes": el.get('class', []),
                        "id": el.get('id', '')
                    })

        return interactive_elements

    def _get_element_text(self, element: Tag) -> str:
        text = element.get_text(strip=True)
        return ' '.join(text.split())

    @staticmethod
    def compare_doms(initial_html: str, final_html: str) -> List[Dict[str, Any]]:
        """
        Compares two HTML documents and identifies new, visible elements.
        Improved: structural + text diff fallback.
        """
        initial_soup = BeautifulSoup(initial_html, 'lxml')
        final_soup = BeautifulSoup(final_html, 'lxml')

        initial_texts = set()
        for tag in initial_soup.find_all(True):
            text = tag.get_text(strip=True)
            if text:
                initial_texts.add(text)

        new_elements = []
        seen_texts = set()

        # Prefer links and buttons that are visible and new by text
        for tag in final_soup.find_all(['a', 'button', 'div', 'span']):
            try:
                text = tag.get_text(strip=True)
            except Exception:
                text = ''
            if not text or text in seen_texts:
                continue
            if text not in initial_texts:
                href = ''
                if tag.name == 'a':
                    href = tag.get('href', '')
                elif tag.find_parent('a'):
                    href = tag.find_parent('a').get('href', '')
                new_elements.append({
                    "text": text,
                    "tag": tag.name,
                    "href": href,
                    "classes": tag.get('class', [])
                })
                seen_texts.add(text)

        # Structural diff fallback: detect new tag/class combos
        if not new_elements:
            initial_tags = {(t.name, tuple(t.get('class', []))) for t in initial_soup.find_all(True)}
            final_tags = {(t.name, tuple(t.get('class', []))) for t in final_soup.find_all(True)}
            new_struct = final_tags - initial_tags
            for tag_name, classes in list(new_struct)[:10]:
                new_elements.append({
                    "text": "",
                    "tag": tag_name,
                    "href": "",
                    "classes": list(classes) if classes else []
                })

        return new_elements

    @staticmethod
    def analyze_modal_dialog(initial_html: str, final_html: str) -> Dict[str, Any] | None:
        """
        Analyzes the difference between two HTML states to find a modal dialog.
        Improved to include fallback heuristics for portals and large overlays.
        """
        initial_soup = BeautifulSoup(initial_html, 'lxml')
        final_soup = BeautifulSoup(final_html, 'lxml')

        initial_texts = set()
        for el in initial_soup.find_all(True):
            text = el.get_text(strip=True)
            if text:
                initial_texts.add(text)

        modal_selectors = [
            "[role='dialog']",
            "[role='alertdialog']",
            ".modal",
            ".popup",
            ".dialog",
            "[class*='modal']",
            "[class*='popup']",
            "[class*='dialog']",
            "[class*='overlay']",
            "div[style*='fixed']",
            "div[style*='absolute']",
        ]

        potential_modals = []
        for selector in modal_selectors:
            try:
                potential_modals.extend(final_soup.select(selector))
            except Exception:
                continue

        modal_container = None
        for el in potential_modals:
            el_text = el.get_text(strip=True)
            if el_text and len(el_text) > 10:
                words = el_text.split()
                # New word heuristic: % of words not present in initial DOM
                new_words = sum(1 for w in words if all(w not in t for t in initial_texts))
                if new_words > max(1, len(words) * 0.25):
                    modal_container = el
                    break

        # Fallback: find large new div/section not present before
        if not modal_container:
            for tag in final_soup.find_all(['div', 'section', 'aside']):
                tag_text = tag.get_text(strip=True)
                if tag_text and len(tag_text) > 30 and tag_text not in initial_texts:
                    modal_container = tag
                    break

        if not modal_container:
            return None

        # Extract modal details
        modal_title = ""
        for heading in ['h1', 'h2', 'h3', 'h4']:
            title_el = modal_container.find(heading)
            if title_el:
                modal_title = title_el.get_text(strip=True)
                break

        if not modal_title:
            # first significant child text
            for child in modal_container.children:
                if hasattr(child, 'get_text'):
                    t = child.get_text(strip=True)
                    if t and 1 < len(t) < 200:
                        modal_title = t
                        break

        modal_text = modal_container.get_text(strip=True)

        # find buttons/links inside modal
        buttons = []
        button_elements = modal_container.select("button, a[role='button'], a, input[type='button'], input[type='submit']")
        seen_button_texts = set()
        for btn in button_elements:
            btn_text = btn.get_text(strip=True)
            if btn_text and btn_text not in seen_button_texts and len(btn_text) < 80:
                buttons.append({
                    "text": btn_text,
                    "tag": btn.name,
                    "type": btn.get('type', ''),
                    "href": btn.get('href', '')
                })
                seen_button_texts.add(btn_text)

        return {
            "title": modal_title,
            "full_text": modal_text,
            "buttons": buttons
        }


if __name__ == "__main__":
    pass
