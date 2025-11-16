import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from urllib.parse import urlparse

from src.browser_manager import BrowserManager
from src.element_analyzer import ElementAnalyzer
from src.llm_service import LLMService
from src.gherkin_generator import GherkinGenerator

app = FastAPI(
    title="AI Gherkin Automation",
    description="An AI-based solution to dynamically generate Gherkin-style testing scenarios for websites.",
    version="1.0.0"
)

class URLInput(BaseModel):
    url: str


@app.post("/generate-tests", summary="Generate Gherkin tests for a URL")
async def generate_tests(item: URLInput):
    gherkin_scenarios = []
    browser = BrowserManager()

    try:
        print(f"\n{'='*60}")
        print(f"Starting test generation for: {item.url}")
        print(f"{'='*60}\n")

        await browser.start()
        await browser.go_to(item.url)

        initial_content = await browser.get_page_content()
        analyzer = ElementAnalyzer(initial_content)
        interactive_elements = analyzer.find_potential_interactive_elements()

        print(f"Found {len(interactive_elements)} potential interactive elements")

        # ------------------------------------------------------------
        # PHASE 1: POPUPS / CLICK INTERACTIONS
        # ------------------------------------------------------------
        clickable_elements = [el for el in interactive_elements if el['tag'] in ['a', 'button']]
        popup_found = False

        for idx, element_data in enumerate(clickable_elements[:20], 1):
            print(f"\n[{idx}] Testing click on: '{element_data.get('text')[:60]}...'")

            try:
                await browser.go_to(item.url)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"  ✗ Failed to navigate: {e}")
                continue

            try:
                changes = await browser.click_and_get_changes(element_data)

                if changes.get('skipped'):
                    print("  → Skipped external navigation link")
                    continue
                if changes.get('navigated'):
                    print("  → Click caused navigation; skipping for popup detection")
                    continue

                modal_details = ElementAnalyzer.analyze_modal_dialog(changes['initial'], changes['final'])
                if modal_details and modal_details['buttons']:
                    print(f"  ✓ Found modal: '{modal_details['title']}'")

                    interaction_data = {
                        'url': item.url,
                        'type': 'popup',
                        'click_element': element_data,
                        'modal': modal_details
                    }

                    llm = LLMService()
                    scenario = llm.generate_gherkin_scenario(interaction_data)
                    if scenario:
                        gherkin_scenarios.append(scenario)
                        popup_found = True
                        print("  ✓ Generated Gherkin scenario for popup")
                        break
                else:
                    print("  ✗ No modal detected")

            except Exception as e:
                print(f"  ✗ Error testing element: {e}")
                continue

        if not popup_found:
            print("\n⚠ No popup/modal interactions found")

        # ------------------------------------------------------------
        # PHASE 2: HOVER INTERACTIONS
        # ------------------------------------------------------------
        try:
            await browser.go_to(item.url)
            await asyncio.sleep(1)
            initial_content = await browser.get_page_content()
            analyzer = ElementAnalyzer(initial_content)
            interactive_elements = analyzer.find_potential_interactive_elements()
        except Exception as e:
            print(f"✗ Failed to reset page for hover tests: {e}")
            interactive_elements = []

        hover_found = False

        for idx, element_data in enumerate(interactive_elements[:30], 1):
            print(f"\n[{idx}] Testing hover on: '{element_data.get('text')[:60]}...'")

            try:
                changes = await browser.hover_and_get_changes(element_data)
                newly_appeared = ElementAnalyzer.compare_doms(changes['initial'], changes['final'])

                if not newly_appeared:
                    print("  → No obvious new text elements, trying structural diff fallback")
                    newly_appeared = ElementAnalyzer.compare_doms(changes['initial'], changes['final'])

                if newly_appeared:
                    print(f"  ✓ Found {len(newly_appeared)} new elements")

                    interaction_data = {
                        'url': item.url,
                        'type': 'hover',
                        'hover_element': element_data,
                        'revealed_elements': newly_appeared
                    }

                    llm = LLMService()
                    scenario = llm.generate_gherkin_scenario(interaction_data)
                    if scenario:
                        gherkin_scenarios.append(scenario)
                        hover_found = True
                        print("  ✓ Generated Gherkin scenario for hover")
                        break
                else:
                    print("  ✗ No new elements revealed")

            except Exception as e:
                print(f"  ✗ Error testing hover: {e}")
                continue

        if not hover_found:
            print("\n⚠ No hover menu interactions found")

    except Exception as e:
        print(f"\n✗ Error during test generation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        try:
            await browser.close()
        except Exception:
            pass

    # ------------------------------------------------------------
    # RESULT HANDLING
    # ------------------------------------------------------------
    if not gherkin_scenarios:
        print("\n" + "="*60)
        print("RESULT: Could not generate any test scenarios")
        print("="*60)
        return {
            'message': 'Could not generate any test scenarios for the given URL.',
            'details': 'No interactive elements (hover menus or popups) were detected on the page.'
        }

    # ------------------------------------------------------------
    # SAVE FEATURE FILE
    # ------------------------------------------------------------
    try:
        domain = urlparse(item.url).netloc
        feature_title = f"Feature: Automated tests for {domain}"
        full_feature_content = f"{feature_title}\n\n" + "\n\n".join(gherkin_scenarios)

        generator = GherkinGenerator()
        filepath = generator.save_feature_file(item.url, full_feature_content)

        print(f"\n✓ Successfully saved feature file")
        print(f"  Path: {filepath}")
        print(f"  Scenarios generated: {len(gherkin_scenarios)}")

        return {
            'message': 'Test generation complete.',
            'feature_file': filepath,
            'scenarios_count': len(gherkin_scenarios),
            'scenarios': gherkin_scenarios
        }

    except Exception as e:
        print(f"\n✗ Failed to save feature file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save feature file: {e}")


@app.get("/")
async def root():
    return {
        'message': 'AI Gherkin Test Generator API',
        'version': '1.0.0',
        'endpoints': {
            'generate_tests': '/generate-tests (POST)',
            'docs': '/docs',
            'redoc': '/redoc'
        }
    }


if __name__ == '__main__':
    print("\n" + "="*60)
    print("AI GHERKIN TEST GENERATOR")
    print("="*60)
    uvicorn.run(app, host='0.0.0.0', port=8000)
