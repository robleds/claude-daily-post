from abc import ABC, abstractmethod
from pathlib import Path


class BasePublisher(ABC):
    """Base class for all social media publishers."""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if all required env vars are set."""

    @abstractmethod
    def publish(self, content: str, image_path: Path | None, video_path: Path | None) -> dict:
        """Publish content. Returns dict with status and URL/ID."""

    def safe_publish(self, content: str, image_path: Path | None = None, video_path: Path | None = None) -> dict:
        if not self.is_configured():
            print(f"[{self.platform_name}] Not configured — skipping publish")
            return {"status": "skipped", "reason": "missing credentials"}
        try:
            result = self.publish(content, image_path, video_path)
            print(f"[{self.platform_name}] Published: {result}")
            return result
        except Exception as e:
            print(f"[{self.platform_name}] Publish error: {e}")
            return {"status": "error", "error": str(e)}
