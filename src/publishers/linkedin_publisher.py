import os
import json
import requests
from pathlib import Path
from .base import BasePublisher


class LinkedInPublisher(BasePublisher):
    API_BASE = "https://api.linkedin.com/v2"

    def __init__(self):
        super().__init__("linkedin")
        self.token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        self.person_urn = os.environ.get("LINKEDIN_PERSON_URN")

    def is_configured(self) -> bool:
        return bool(self.token and self.person_urn)

    def publish(self, content: str, image_path: Path | None = None, video_path: Path | None = None) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        media = None
        if image_path and image_path.exists():
            media = self._upload_image(image_path, headers)

        post_body = {
            "author": self.person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "IMAGE" if media else "NONE",
                    **({"media": [media]} if media else {}),
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        resp = requests.post(
            f"{self.API_BASE}/ugcPosts",
            headers=headers,
            json=post_body,
            timeout=30,
        )
        resp.raise_for_status()
        post_id = resp.headers.get("X-RestLi-Id", "unknown")
        return {"status": "published", "post_id": post_id}

    def _upload_image(self, image_path: Path, headers: dict) -> dict | None:
        """Register and upload image to LinkedIn."""
        register_resp = requests.post(
            f"{self.API_BASE}/assets?action=registerUpload",
            headers=headers,
            json={
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": self.person_urn,
                    "serviceRelationships": [
                        {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
                    ],
                }
            },
            timeout=30,
        )
        register_resp.raise_for_status()
        data = register_resp.json()
        upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = data["value"]["asset"]

        upload_resp = requests.put(
            upload_url,
            data=image_path.read_bytes(),
            headers={"Content-Type": "image/png", "Authorization": f"Bearer {self.token}"},
            timeout=60,
        )
        upload_resp.raise_for_status()

        return {
            "status": "READY_TO_POST",
            "description": {"text": ""},
            "media": asset_urn,
            "title": {"text": ""},
        }
