import os
import json
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
    else:
        print("[video_generator] DID_API_KEY or presenter image not set — script saved for manual use")
        return {"script_path": str(script_path), "video_path": None}


def _generate_with_did(script: str, output_dir: Path, api_key: str, presenter_url: str) -> dict:
    """Submit talking-head video to D-ID API and download when ready."""
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "script": {
            "type": "text",
            "input": script,
            "provider": {"type": "microsoft", "voice_id": "pt-BR-AntonioNeural"},
        },
        "source_url": presenter_url,
        "config": {"fluent": True, "pad_audio": 0.0},
    }

    try:
        resp = requests.post(
            "https://api.d-id.com/talks",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        talk_id = resp.json()["id"]
        print(f"[video_generator] D-ID talk created: {talk_id}")

        import time
        for _ in range(30):
            time.sleep(5)
            status_resp = requests.get(
                f"https://api.d-id.com/talks/{talk_id}",
                headers=headers,
                timeout=10,
            )
            status_resp.raise_for_status()
            data = status_resp.json()
            if data["status"] == "done":
                video_url = data["result_url"]
                video_resp = requests.get(video_url, timeout=60)
                video_path = output_dir / "video.mp4"
                video_path.write_bytes(video_resp.content)
                print(f"[video_generator] Video saved: {video_path}")
                return {"script_path": str(output_dir / "video_script.txt"), "video_path": str(video_path)}
            elif data["status"] == "error":
                print(f"[video_generator] D-ID error: {data}")
                break

    except Exception as e:
        print(f"[video_generator] Error with D-ID API: {e}")

    return {"script_path": str(output_dir / "video_script.txt"), "video_path": None}
