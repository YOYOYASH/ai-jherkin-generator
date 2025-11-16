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

        # Create output directory if not exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _sanitize_filename(self, url: str) -> str:
        """
        Converts a URL into a safe filename.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.replace(".", "_")
        path = parsed.path.strip("/").replace("/", "_")

        if not path:
            path = "home"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return f"{domain}__{path}__{timestamp}.feature"

    def save_feature_file(self, url: str, content: str) -> str:
        """
        Saves the Gherkin feature content to a .feature file.
        Returns the file path.
        """

        filename = self._sanitize_filename(url)
        file_path = os.path.join(self.output_dir, filename)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return file_path

        except Exception as e:
            raise RuntimeError(f"Failed to save feature file: {e}")
