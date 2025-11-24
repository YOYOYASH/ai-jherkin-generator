import os
from typing import Dict, Any
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except Exception:
    genai = None

class LLMService:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('GEMINI_API_KEY')

        if not api_key:
            print("⚠ GEMINI_API_KEY not set. LLM calls will be stubbed.")
            self.model = None
            return

        if genai is None:
            print("⚠ google.generativeai not installed.")
            self.model = None
            return

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        base_url = data.get('url')
        
        if data.get("type") == "hover":
            hover_text = data.get("hover_element", {}).get("text", "Menu")
            target_link = data.get("target_link", {})
            link_text = target_link.get("text", "Sub-item")
            target_url = target_link.get("href", "http://target.url")

            return f"""
            Task: Write a Gherkin Scenario for a HOVER interaction.
            - Start URL: {base_url}
            - Hover over: "{hover_text}"
            - Click revealed link: "{link_text}"
            - Verify URL changes to: "{target_url}"

            Format:
            Scenario: Verify navigation from "{hover_text}" to "{link_text}"
              Given the user is on the "{base_url}" page
              When the user hovers over the navigation menu "{hover_text}"
              And clicks the link "{link_text}" from the dropdown
              Then the page URL should change to "{target_url}"
            """

        elif data.get("type") == "popup":
            trigger_text = data.get("click_element", {}).get("text", "Button")
            modal = data.get("modal", {})
            title = modal.get("title", "Popup Title")
            
            # Safe extraction
            buttons = [b.get('text', '') for b in modal.get("buttons", [])]
            
            cancel_text = next((b for b in buttons if 'cancel' in b.lower() or 'close' in b.lower()), "Cancel")
            continue_text = next((b for b in buttons if 'continue' in b.lower() or 'leave' in b.lower()), "Continue")

            return f"""
            Task: Write TWO Gherkin Scenarios for a POPUP interaction (Cancel vs Continue).
            - Start URL: {base_url}
            - Trigger Button: "{trigger_text}"
            - Popup Title: "{title}"
            - Cancel Button Name: "{cancel_text}"
            - Continue Button Name: "{continue_text}"

            Format:
            Scenario: Verify the cancel button in the "{title}" pop-up
              Given the user is on the "{base_url}" page
              When the user clicks the "{trigger_text}" button
              Then a pop-up should appear with the title "{title}"
              And the user clicks the "{cancel_text}" button
              Then the pop-up should close and the user should remain on the same page

            Scenario: Verify the continue button in the "{title}" pop-up
              Given the user is on the "{base_url}" page
              When the user clicks the "{trigger_text}" button
              Then a pop-up should appear with the title "{title}"
              And the user clicks the "{continue_text}" button
              Then the page URL should change to a new domain
            """

        return ""

    def generate_gherkin_scenario(self, interaction_data: Dict[str, Any]) -> str:
        prompt = self._build_prompt(interaction_data)
        if not prompt: return ""

        # Crash prevention
        if not self.model:
            return ""

        system_prompt = "You are a QA Automation Expert. Output ONLY raw Gherkin text. No Markdown. No 'Feature:' headers."

        try:
            response = self.model.generate_content(f"{system_prompt}\n\n{prompt}")
            text = response.text.strip()
            text = text.replace("```gherkin", "").replace("```", "").replace("Feature:", "# Feature:").strip()
            return text
        except Exception as e:
            print(f"  ⚠ LLM Error: {e}")
            return ""