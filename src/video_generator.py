import os
import requests
from pathlib import Path


def generate_video(script: str, output_dir: Path, presenter_image_url: str = None) -> dict:
    """
    Generate a talking-head video using D-ID API if DID_API_KEY is set.
    Otherwise saves the script for manual recording.
    """
    videos_dir = output_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    script_path = videos_dir / "video_script.txt"
    script_path.write_text(script, encoding="utf-8")

    did_key = os.environ.get("DID_API_KEY")
    presenter = presenter_image_url or os.environ.get("DID_PRESENTER_IMAGE_URL")

    if did_key and presenter:
        return _generate_with_did(script, videos_dir, did_key, presenter)

    print("[video_generator] DID_API_KEY ou presenter não configurado — script salvo")
    return {"script_path": str(script_path), "video_path": None}


def _generate_with_did(script: str, output_dir: Path, api_key: str, presenter_url: str) -> dict:
    script_path = str(output_dir / "video_script.txt")

    # D-ID aceita a key diretamente em Basic auth (já vem em base64 do dashboard)
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "script": {
            "type": "text",
            "input": script,
            "provider": {
                "type": "microsoft",
                "voice_id": "pt-BR-AntonioNeural",
            },
        },
        "source_url": presenter_url,
        "config": {"fluent": True, "pad_audio": 0.5},
    }

    try:
        resp = requests.post(
            "https://api.d-id.com/talks",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if not resp.ok:
            print(f"[video_generator] D-ID error {resp.status_code}: {resp.text}")
            return {"script_path": script_path, "video_path": None}

        talk_id = resp.json()["id"]
        print(f"[video_generator] D-ID talk criado: {talk_id}")

        import time
        for attempt in range(30):
            time.sleep(5)
            status_resp = requests.get(
                f"https://api.d-id.com/talks/{talk_id}",
                headers=headers,
                timeout=10,
            )
            if not status_resp.ok:
                continue

            data = status_resp.json()
            status = data.get("status")

            if status == "done":
                video_url = data["result_url"]
                video_resp = requests.get(video_url, timeout=60)
                video_path = output_dir / "video.mp4"
                video_path.write_bytes(video_resp.content)
                print(f"[video_generator] Vídeo salvo: {video_path}")
                return {"script_path": script_path, "video_path": str(video_path)}

            elif status == "error":
                print(f"[video_generator] D-ID falhou: {data.get('error', data)}")
                break

            print(f"[video_generator] Aguardando D-ID... tentativa {attempt + 1}/30 (status: {status})")

    except Exception as e:
        print(f"[video_generator] Exceção D-ID: {e}")

    return {"script_path": script_path, "video_path": None}
