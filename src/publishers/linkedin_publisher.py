import os
import requests
from pathlib import Path
from .base import BasePublisher


class LinkedInPublisher(BasePublisher):
    REST_BASE = "https://api.linkedin.com/rest"

    def __init__(self):
        super().__init__("linkedin")
        self.token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        self.person_urn = os.environ.get("LINKEDIN_PERSON_URN")

    def is_configured(self) -> bool:
        return bool(self.token and self.person_urn)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": "202504",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def publish(self, content: str, image_path: Path | None = None, video_path: Path | None = None) -> dict:
        image_urn = None
        if image_path and image_path.exists():
            image_urn = self._upload_image(image_path)

        post_body = {
            "author": self.person_urn,
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        if image_urn:
            post_body["content"] = {"media": {"id": image_urn}}

        resp = requests.post(
            f"{self.REST_BASE}/posts",
            headers=self._headers(),
            json=post_body,
            timeout=30,
        )

        if not resp.ok:
            raise RuntimeError(f"LinkedIn POST /rest/posts {resp.status_code}: {resp.text}")

        post_id = resp.headers.get("x-restli-id", "unknown")
        return {"status": "published", "post_id": post_id}

    def _upload_image(self, image_path: Path) -> str | None:
        """Upload image via new LinkedIn Images API, return image URN."""
        init_resp = requests.post(
            f"{self.REST_BASE}/images?action=initializeUpload",
            headers=self._headers(),
            json={"initializeUploadRequest": {"owner": self.person_urn}},
            timeout=30,
        )
        if not init_resp.ok:
            print(f"[linkedin] Image upload init failed {init_resp.status_code}: {init_resp.text}")
            return None

        data = init_resp.json()["value"]
        upload_url = data["uploadUrl"]
        image_urn = data["image"]

        upload_resp = requests.put(
            upload_url,
            data=image_path.read_bytes(),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "image/png",
            },
            timeout=60,
        )
        if not upload_resp.ok:
            print(f"[linkedin] Image binary upload failed {upload_resp.status_code}")
            return None

        return image_urn
