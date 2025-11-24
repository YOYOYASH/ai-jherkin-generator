import asyncio
import uvicorn
import traceback
from fastapi import FastAPI
from pydantic import BaseModel
from urllib.parse import urljoin, urlparse
from src.browser_manager import BrowserManager
from src.element_analyzer import ElementAnalyzer
from src.llm_service import LLMService
from src.gherkin_generator import GherkinGenerator

app = FastAPI()

class URLInput(BaseModel):
    url: str

@app.post("/generate-tests")
async def generate_tests(item: URLInput):
    browser = BrowserManager()
    hover_scenarios = []
    popup_scenarios = []

    try:
        print(f"STARTING FULL ANALYSIS: {item.url}")
        
        await browser.start()
        await browser.go_to(item.url)
        
        print("  -> Scrolling to load lazy content...")
        await browser.scroll_to_bottom()
        
        content = await browser.get_page_content()
        analyzer = ElementAnalyzer(content)
        elements = analyzer.find_potential_interactive_elements(item.url)
        
        print(f"Found {len(elements)} interactive candidates.")

        # ==========================================================
        # PHASE 1: HOVER TESTS
        # ==========================================================
        print("\n--- PHASE 1: Hover Tests ---")
        nav_items = [e for e in elements if e.get('type') == 'nav']
        
        hover_count = 0
        for el in nav_items[:20]:
            if hover_count >= 5: break 
            if not await browser.is_element_visible(el): continue

            print(f"Testing Hover: {el['text']}")
            await browser.go_to(item.url)
            
            changes = await browser.hover_and_get_changes(el)
            
            # FIX: Use 'initial_visible' set for detection
            initial_visible_set = changes.get('initial_visible', set())
            
            new_links = ElementAnalyzer.compare_doms(initial_visible_set, changes['final'])
            
            if new_links:
                target = new_links[0]
                target['href'] = urljoin(item.url, target['href'])
                print(f"  -> Menu Revealed: {target['text']}")
                
                llm = LLMService()
                scenario = llm.generate_gherkin_scenario({
                    "url": item.url,
                    "type": "hover",
                    "hover_element": el,
                    "target_link": target
                })
                if scenario and "Scenario:" in scenario:
                    hover_scenarios.append(scenario)
                    hover_count += 1

        # ==========================================================
        # PHASE 2: POPUP TESTS
        # ==========================================================
        print("\n--- PHASE 2: Popup Tests ---")
        trigger_items = [e for e in elements if e.get('type') == 'trigger']
        
        popup_count = 0
        for el in trigger_items:
            if popup_count >= 10: break
            if not await browser.is_element_visible(el): continue

            print(f"Testing Click: {el['text']} (href: {el.get('href', 'n/a')})")
            await browser.go_to(item.url)
            changes = await browser.click_and_get_changes(el)
            
            if changes['navigated']:
                print("  -> Navigated away.")
                continue
            
            modal = ElementAnalyzer.analyze_modal_dialog(changes['initial'], changes['final'])
            if modal:
                print(f"  -> POPUP DETECTED: {modal['title']}")
                
                llm = LLMService()
                scenario = llm.generate_gherkin_scenario({
                    "url": item.url,
                    "type": "popup",
                    "click_element": el,
                    "modal": modal
                })
                
                if scenario and "Scenario:" in scenario:
                    popup_scenarios.append(scenario)
                    popup_count += 1

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
    
    finally:
        print("Analysis Complete. Closing Browser...")
        await browser.close()

    # ==========================================================
    # SAVE FILES
    # ==========================================================
    response_data = {"status": "success", "files": []}
    domain = urlparse(item.url).netloc
    gen = GherkinGenerator()

    if hover_scenarios:
        hover_text = f"Feature: Navigation Menu Tests for {domain}\n\n" + "\n\n".join(hover_scenarios)
        hover_path = gen.save_feature_file(item.url, hover_text, test_type="hover")
        response_data["files"].append({"type": "hover", "path": hover_path})

    if popup_scenarios:
        popup_text = f"Feature: Modal/Popup Tests for {domain}\n\n" + "\n\n".join(popup_scenarios)
        popup_path = gen.save_feature_file(item.url, popup_text, test_type="popup")
        response_data["files"].append({"type": "popup", "path": popup_path})

    return response_data if response_data["files"] else {"status": "failed", "message": "No scenarios generated."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)