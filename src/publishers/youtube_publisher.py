import os
import base64
from pathlib import Path
from .base import BasePublisher


class YouTubePublisher(BasePublisher):
    """Uploads videos to YouTube via YouTube Data API v3."""

    def __init__(self):
        super().__init__("youtube")
        self.credentials_file = os.environ.get("YOUTUBE_CREDENTIALS_FILE", "credentials.json")
        self.token_b64 = os.environ.get("YOUTUBE_TOKEN_B64")

    def is_configured(self) -> bool:
        # Aceita token base64 (GitHub Actions) ou arquivo local (uso local)
        return bool(self.token_b64) or Path("youtube_token.pickle").exists()

    def publish(self, content: str, image_path: Path | None = None, video_path: Path | None = None) -> dict:
        if not (video_path and video_path.exists()):
            print("[youtube] Sem vídeo disponível — pulando YouTube")
            return {"status": "skipped", "reason": "no video"}

        lines = content.split("\n")
        title = next((l for l in lines if l.strip()), "IA e Produtividade")[:100]

        return self._upload_video(video_path, title, content)

    def _upload_video(self, video_path: Path, title: str, description: str) -> dict:
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.auth.transport.requests import Request
            import pickle

            token_file = Path("youtube_token.pickle")
            creds = None

            # Restaura token do base64 (GitHub Actions) se não há arquivo local
            if self.token_b64 and not token_file.exists():
                token_file.write_bytes(base64.b64decode(self.token_b64))
                print("[youtube] Token restaurado do YOUTUBE_TOKEN_B64")

            if token_file.exists():
                with open(token_file, "rb") as f:
                    creds = pickle.load(f)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    with open(token_file, "wb") as f:
                        pickle.dump(creds, f)
                else:
                    # Só funciona localmente (requer browser)
                    if not Path(self.credentials_file).exists():
                        raise RuntimeError(
                            "YouTube requer autenticação inicial local. "
                            "Execute: python3 youtube_auth.py e adicione o token como YOUTUBE_TOKEN_B64."
                        )
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
            raise RuntimeError(f"YouTube upload falhou: {e}") from e
