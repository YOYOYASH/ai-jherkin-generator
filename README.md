# AI Gherkin Automation

An AI-based solution to dynamically generate Gherkin-style testing scenarios for websites containing hovering elements.

## Overview

This project uses AI and browser automation to analyze a web page, identify interactive elements (specifically those that react to hover events), and generate BDD test cases in Gherkin format (`.feature` files).

## Tech Stack

- **Python >=3.13**
- **FastAPI**: For the web API.
- **Playwright**: For browser automation.
- **BeautifulSoup**: For HTML parsing.
- **Google Gemini**: For LLM-based reasoning and Gherkin generation.
- **uv**: For dependency management.

## Project Structure

```
/ai-jherkin-automation
├── .gitignore
├── main.py                 # Main entry point, FastAPI app
├── README.md
├── pyproject.toml
├── generated_features/     # Directory for output .feature files
└── src/
    ├── __init__.py
    ├── browser_manager.py    # Playwright automation logic
    ├── element_analyzer.py   # DOM analysis and element identification
    ├── gherkin_generator.py  # Gherkin file generation
    └── llm_service.py        # LLM interaction logic
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd ai-jherkin-automation
    ```

2.  **Install uv:**
    ```bash
    pip install uv
    ```

3.  **Create and activate a virtual environment:**
    ```bash
    uv venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

4.  **Install the dependencies:**
    ```bash
    uv pip install -e .
    ```

5.  **Install Playwright browsers:**
    ```bash
    playwright install
    ```

6.  **Set up environment variables:**
    Create a `.env` file in the root directory and add your Gemini API key:
    ```
    GEMINI_API_KEY="your-api-key-here"
    ```

## Usage

1.  **Start the application:**
    ```bash
    uv run dev
    ```

2.  **Send a request to the API:**
    You can use the interactive API documentation at `http://12p://127.0.0.1:8000/docs`.

    Send a `POST` request to the `/generate-tests` endpoint with a JSON body like this:
    ```json
    {
      "url": "https://www.example.com"
    }
    ```

3.  **Check the output:**
    The generated `.feature` file will be saved in the `generated_features` directory.
