import os
import requests
from pathlib import Path
from .base import BasePublisher


class InstagramPublisher(BasePublisher):
    """Publishes to Instagram via Facebook Graph API (requires Business account)."""

    GRAPH_BASE = "https://graph.facebook.com/v19.0"

    def __init__(self):
        super().__init__("instagram")
        self.token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        self.account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")

    def is_configured(self) -> bool:
        return bool(self.token and self.account_id)

    def publish(self, content: str, image_path: Path | None = None, video_path: Path | None = None) -> dict:
        if video_path and video_path.exists():
            return self._publish_reel(content, video_path)
        elif image_path and image_path.exists():
            return self._publish_image(content, image_path)
        else:
            raise ValueError("Instagram requires an image or video")

    def _publish_image(self, caption: str, image_path: Path) -> dict:
        image_url = self._upload_to_temp_host(image_path)

        container_resp = requests.post(
            f"{self.GRAPH_BASE}/{self.account_id}/media",
            params={
                "image_url": image_url,
                "caption": caption,
                "access_token": self.token,
            },
            timeout=30,
        )
        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        publish_resp = requests.post(
            f"{self.GRAPH_BASE}/{self.account_id}/media_publish",
            params={"creation_id": container_id, "access_token": self.token},
            timeout=30,
        )
        publish_resp.raise_for_status()
        media_id = publish_resp.json()["id"]
        return {"status": "published", "media_id": media_id}

    def _publish_reel(self, caption: str, video_path: Path) -> dict:
        video_url = self._upload_to_temp_host(video_path)

        container_resp = requests.post(
            f"{self.GRAPH_BASE}/{self.account_id}/media",
            params={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": self.token,
            },
            timeout=30,
        )
        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        import time
        for _ in range(20):
            time.sleep(5)
            status_resp = requests.get(
                f"{self.GRAPH_BASE}/{container_id}",
                params={"fields": "status_code", "access_token": self.token},
                timeout=10,
            )
            if status_resp.json().get("status_code") == "FINISHED":
                break

        publish_resp = requests.post(
            f"{self.GRAPH_BASE}/{self.account_id}/media_publish",
            params={"creation_id": container_id, "access_token": self.token},
            timeout=30,
        )
        publish_resp.raise_for_status()
        return {"status": "published", "media_id": publish_resp.json()["id"]}

    def _upload_to_temp_host(self, file_path: Path) -> str:
        """
        Instagram requires a public URL for media upload.
        This method should be replaced with your preferred file hosting (S3, Cloudinary, etc.)
        """
        raise NotImplementedError(
            "Instagram requires a public URL for media. "
            "Set up a file hosting service (S3, Cloudinary) and implement this method."
        )
