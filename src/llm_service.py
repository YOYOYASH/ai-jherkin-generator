import os
from typing import Dict, Any

try:
    import google.generativeai as genai
except Exception:
    genai = None

from dotenv import load_dotenv


class LLMService:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('GEMINI_API_KEY')

        if not api_key:
            print("⚠ GEMINI_API_KEY not set. LLM calls will be stubbed.")
            self.model = None
            return

        if genai is None:
            raise RuntimeError("google.generativeai package not available")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    # ------------------------------------------------------------
    # BUILD PROMPT
    # ------------------------------------------------------------
    def _build_prompt(self, data: Dict[str, Any]) -> str:
        if data.get("type") == "hover":
            hover = data.get("hover_element", {})
            revealed = data.get("revealed_elements", [])

            if not revealed:
                return ""

            target = revealed[0]
            return (
                f"Generate a Gherkin scenario:\n"
                f"URL = {data.get('url')}\n"
                f"Hover element = {hover.get('text')}\n"
                f"Revealed element to click = {target.get('text')}\n"
            )

        elif data.get("type") == "popup":
            modal = data.get("modal", {})
            buttons = modal.get("buttons", [])
            button_names = [b["text"] for b in buttons]

            return (
                f"Generate two Gherkin popup test scenarios.\n"
                f"Popup title: {modal.get('title')}\n"
                f"Popup buttons: {button_names}\n"
            )

        return ""

    # ------------------------------------------------------------
    # GENERATE GHERKIN
    # ------------------------------------------------------------
    def generate_gherkin_scenario(self, interaction_data: Dict[str, Any]) -> str:
        prompt = self._build_prompt(interaction_data)
        if not prompt:
            return ""

        system_prompt = (
            "You are an expert QA Automation Engineer specializing in BDD.\n"
            "Only output valid Gherkin syntax. No explanations."
        )

        full_prompt = f"{system_prompt}\n\n{prompt}"

        # ------------------------------------------------------------
        # FALLBACK MODE (NO GEMINI)
        # ------------------------------------------------------------
        if not self.model:
            print("⚠ Using stubbed LLM fallback.")

            if interaction_data.get("type") == "hover":
                hover = interaction_data["hover_element"]
                revealed = interaction_data["revealed_elements"]
                target_text = revealed[0].get("text", "revealed element")

                return f"""
Feature: Validate hover-based interaction

Scenario: Hover reveals a new clickable item
  Given the user is on the "{interaction_data['url']}" page
  When the user hovers over the "{hover.get('text')}" element
  And the user clicks the "{target_text}" link
  Then the page should navigate to a new URL
""".strip()

            elif interaction_data.get("type") == "popup":
                modal = interaction_data["modal"]
                btns = modal.get("buttons", [])
                cancel = btns[0]["text"] if len(btns) > 0 else "Cancel"
                cont = btns[1]["text"] if len(btns) > 1 else "Continue"
                click_text = interaction_data["click_element"]["text"]

                return f"""
Feature: Validate popup modal behavior

Scenario: Validate cancel action in modal
  Given the user is on the "{interaction_data['url']}" page
  When the user clicks the "{click_text}" button
  Then a popup should appear with title "{modal.get('title')}"
  And the user clicks the "{cancel}" button
  Then the popup should close and the user should remain on the same page

Scenario: Validate continue action in modal
  Given the user is on the "{interaction_data['url']}" page
  When the user clicks the "{click_text}" button
  Then a popup should appear with title "{modal.get('title')}"
  And the user clicks the "{cont}" button
  Then the page URL should change to a new domain
""".strip()

            return ""

        # ------------------------------------------------------------
        # ACTUAL GEMINI CALL
        # ------------------------------------------------------------
        try:
            response = self.model.generate_content(full_prompt)
            text = response.text.strip()

            if "```" in text:
                text = text.replace("```gherkin", "").replace("```", "").strip()

            return text

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return ""
