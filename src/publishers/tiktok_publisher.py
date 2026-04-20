import os
import requests
from pathlib import Path
from .base import BasePublisher


class TikTokPublisher(BasePublisher):
    """Publishes videos to TikTok via Content Posting API."""

    API_BASE = "https://open.tiktokapis.com/v2"

    def __init__(self):
        super().__init__("tiktok")
        self.token = os.environ.get("TIKTOK_ACCESS_TOKEN")
        self.open_id = os.environ.get("TIKTOK_OPEN_ID")

    def is_configured(self) -> bool:
        return bool(self.token and self.open_id)

    def publish(self, content: str, image_path: Path | None = None, video_path: Path | None = None) -> dict:
        if not (video_path and video_path.exists()):
            print("[tiktok] No video available — TikTok requires video content")
            return {"status": "skipped", "reason": "no video"}

        return self._upload_video(content, video_path)

    def _upload_video(self, caption: str, video_path: Path) -> dict:
        file_size = video_path.stat().st_size

        init_resp = requests.post(
            f"{self.API_BASE}/post/publish/video/init/",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "post_info": {
                    "title": caption[:150],
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": file_size,
                    "total_chunk_count": 1,
                },
            },
            timeout=30,
        )
        init_resp.raise_for_status()
        data = init_resp.json()["data"]
        publish_id = data["publish_id"]
        upload_url = data["upload_url"]

        upload_resp = requests.put(
            upload_url,
            data=video_path.read_bytes(),
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                "Content-Length": str(file_size),
            },
            timeout=120,
        )
        upload_resp.raise_for_status()

        return {"status": "published", "publish_id": publish_id}
