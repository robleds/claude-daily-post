import os
from pathlib import Path
from .base import BasePublisher


class YouTubePublisher(BasePublisher):
    """Uploads videos to YouTube via YouTube Data API v3."""

    def __init__(self):
        super().__init__("youtube")
        self.credentials_file = os.environ.get("YOUTUBE_CREDENTIALS_FILE", "credentials.json")

    def is_configured(self) -> bool:
        return Path(self.credentials_file).exists()

    def publish(self, content: str, image_path: Path | None = None, video_path: Path | None = None) -> dict:
        if not (video_path and video_path.exists()):
            print("[youtube] No video available — YouTube requires video content")
            return {"status": "skipped", "reason": "no video"}

        lines = content.split("\n")
        title = next((l for l in lines if l.strip()), "IA e Produtividade")[:100]
        description = content

        return self._upload_video(video_path, title, description)

    def _upload_video(self, video_path: Path, title: str, description: str) -> dict:
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            import pickle

            token_file = Path("youtube_token.pickle")
            creds = None

            if token_file.exists():
                with open(token_file, "rb") as f:
                    creds = pickle.load(f)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    from google.auth.transport.requests import Request
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file,
                        scopes=["https://www.googleapis.com/auth/youtube.upload"],
                    )
                    creds = flow.run_local_server(port=0)
                with open(token_file, "wb") as f:
                    pickle.dump(creds, f)

            youtube = build("youtube", "v3", credentials=creds)

            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "categoryId": "28",
                },
                "status": {"privacyStatus": "public"},
            }

            media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
            request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
            response = request.execute()
            video_id = response["id"]
            return {"status": "published", "video_id": video_id, "url": f"https://youtu.be/{video_id}"}

        except Exception as e:
            raise RuntimeError(f"YouTube upload failed: {e}") from e
