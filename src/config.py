"""
Configuration settings for the AI Gherkin Test Generator
"""

# ------------------------------------------------------------
# BROWSER SETTINGS
# ------------------------------------------------------------

BROWSER_TIMEOUT = 45000         # 45 seconds
PAGE_LOAD_WAIT = 3000           # Wait after page load (ms)
INTERACTION_WAIT = 1500         # Wait after interactions (ms)
COOKIE_BANNER_WAIT = 2000       # Wait after dismissing cookie banner

# Viewport settings
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# Browser user agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Extra launch args to avoid failures in sandbox/lambda/CI environments
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-web-security",
    "--ignore-certificate-errors",
]


# ------------------------------------------------------------
# ELEMENT DETECTION SETTINGS
# ------------------------------------------------------------

MIN_TEXT_LENGTH = 1
MAX_TEXT_LENGTH = 100

# Max clickable / hoverable items to evaluate
MAX_CLICKABLE_ELEMENTS = 15
MAX_HOVERABLE_ELEMENTS = 20
MAX_RETRIES = 3

# When checking hrefs, skip only if external
SKIP_IF_EXTERNAL = True

# URLs starting with these are skipped completely
SKIP_HREF_PATTERNS = [
    "mailto:",
    "tel:",
    "javascript:",
]


# ------------------------------------------------------------
# COOKIE BANNER SELECTORS
# ------------------------------------------------------------
# These are attempted in order; first visible dismiss button wins.
COOKIE_SELECTORS = [
    "text=Accept All",
    "text=Accept All Cookies",
    "text=Accept Cookies",
    "text=Accept",
    "text=I Accept",
    "text=Agree",
    "text=Allow All",
    "text=OK",
    "text=Got it",
    "text=Continue",
    "button[id*='accept' i]",
    "button[class*='accept' i]",
    "button[id*='cookie' i]",
    "button[class*='cookie' i]",
    "[aria-label*='Accept' i]",
    "[aria-label*='Cookie' i]",
    ".cookie-accept",
    ".cookie-consent-accept",
    "#onetrust-accept-btn-handler",
    ".optanon-allow-all-button",
]


# ------------------------------------------------------------
# OUTPUT SETTINGS
# ------------------------------------------------------------

OUTPUT_DIR = "generated_features"
