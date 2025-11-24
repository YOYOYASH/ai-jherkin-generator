import os
from urllib.parse import urlparse
from datetime import datetime
from . import config

class GherkinGenerator:
    """
    Handles saving generated Gherkin scenarios into .feature files.
    """

    def __init__(self):
        self.output_dir = config.OUTPUT_DIR
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _sanitize_filename(self, url: str, test_type: str) -> str:
        """
        Converts a URL into a safe filename with a specific test type suffix.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.replace(".", "_")
        path = parsed.path.strip("/").replace("/", "_")
        if not path:
            path = "home"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Format: domain__type__timestamp.feature
        return f"{domain}__{test_type}__{timestamp}.feature"

    def save_feature_file(self, url: str, content: str, test_type: str = "tests") -> str:
        """
        Saves the Gherkin feature content to a specific .feature file.
        """
        filename = self._sanitize_filename(url, test_type)
        file_path = os.path.join(self.output_dir, filename)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return file_path
        except Exception as e:
            raise RuntimeError(f"Failed to save feature file: {e}")