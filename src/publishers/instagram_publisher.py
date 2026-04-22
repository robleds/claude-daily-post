import os
import re
import time
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
        self.cloudinary_url = os.environ.get("CLOUDINARY_URL")

    def is_configured(self) -> bool:
        return bool(self.token and self.account_id)

    def publish(self, content: str, image_path: Path | None = None, video_path: Path | None = None) -> dict:
        if video_path and video_path.exists():
            return self._publish_reel(content, video_path)
        elif image_path and image_path.exists():
            return self._publish_image(content, image_path)
        else:
            return {"status": "skipped", "reason": "no image or video available"}

    def _publish_image(self, caption: str, image_path: Path) -> dict:
        image_url = self._upload_to_cloudinary(image_path)
        if not image_url:
            return {"status": "skipped", "reason": "CLOUDINARY_URL not configured — cannot host image for Instagram API"}

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
        video_url = self._upload_to_cloudinary(video_path)
        if not video_url:
            return {"status": "skipped", "reason": "CLOUDINARY_URL not configured — cannot host video for Instagram API"}

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

    def _upload_to_cloudinary(self, file_path: Path) -> str | None:
        """Upload file to Cloudinary and return public URL. Returns None if not configured."""
        if not self.cloudinary_url:
            print("[instagram] CLOUDINARY_URL not set — skipping media upload")
            return None

        # Parse cloudinary://api_key:api_secret@cloud_name
        match = re.match(r"cloudinary://(\w+):([^@]+)@(.+)", self.cloudinary_url)
        if not match:
            print("[instagram] CLOUDINARY_URL format invalid — expected cloudinary://key:secret@cloud_name")
            return None

        api_key, api_secret, cloud_name = match.groups()
        resource_type = "video" if file_path.suffix.lower() == ".mp4" else "image"

        resp = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload",
            data={"upload_preset": "ml_default", "api_key": api_key},
            files={"file": file_path.read_bytes()},
            auth=(api_key, api_secret),
            timeout=120,
        )

        if not resp.ok:
            print(f"[instagram] Cloudinary upload failed {resp.status_code}: {resp.text[:200]}")
            return None

        url = resp.json().get("secure_url")
        print(f"[instagram] Uploaded to Cloudinary: {url}")
        return url
