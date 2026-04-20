import os
import requests
from pathlib import Path
from .base import BasePublisher


class MediumPublisher(BasePublisher):
    """Publishes articles to Medium via Integration Token."""

    API_BASE = "https://api.medium.com/v1"

    def __init__(self):
        super().__init__("medium")
        self.token = os.environ.get("MEDIUM_INTEGRATION_TOKEN")

    def is_configured(self) -> bool:
        return bool(self.token)

    def publish(self, content: str, image_path: Path | None = None, video_path: Path | None = None) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        user_resp = requests.get(f"{self.API_BASE}/me", headers=headers, timeout=10)
        user_resp.raise_for_status()
        user_id = user_resp.json()["data"]["id"]

        lines = [l.strip() for l in content.split("\n") if l.strip()]
        title = lines[0].lstrip("#").strip() if lines else "IA e Produtividade"
        body_html = self._markdown_to_html(content)

        post_resp = requests.post(
            f"{self.API_BASE}/users/{user_id}/posts",
            headers=headers,
            json={
                "title": title,
                "contentFormat": "html",
                "content": body_html,
                "publishStatus": "public",
                "tags": ["ia", "inteligencia-artificial", "produtividade", "transformacao-digital", "negocios"],
            },
            timeout=30,
        )
        post_resp.raise_for_status()
        data = post_resp.json()["data"]
        return {"status": "published", "url": data.get("url"), "post_id": data.get("id")}

    def _markdown_to_html(self, text: str) -> str:
        import re
        text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
        text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        paragraphs = []
        for para in text.split("\n\n"):
            para = para.strip()
            if para and not para.startswith("<h"):
                para = f"<p>{para}</p>"
            paragraphs.append(para)
        return "\n".join(paragraphs)
