import os
import base64
import requests
from pathlib import Path
from config import PLATFORM_IMAGE_SPECS


def generate_images(concepts: dict, output_dir: Path) -> dict:
    """
    Generate images for each platform.
    Uses fal.ai (flux-schnell) if FAL_KEY is set, otherwise saves prompts only.
    """
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    fal_key = os.environ.get("FAL_KEY")
    results = {}

    for platform, prompt in concepts.items():
        specs = PLATFORM_IMAGE_SPECS.get(platform.replace("_thumbnail", ""), PLATFORM_IMAGE_SPECS["linkedin"])
        prompt_file = images_dir / f"{platform}_prompt.txt"
        prompt_file.write_text(f"Prompt: {prompt}\n\nSize: {specs['width']}x{specs['height']} ({specs['ratio']})", encoding="utf-8")

        if fal_key:
            image_path = _generate_with_fal(prompt, specs, platform, images_dir, fal_key)
            results[platform] = {"prompt": prompt, "image_path": str(image_path) if image_path else None}
        else:
            print(f"[image_generator] FAL_KEY not set — saved prompt for {platform}")
            results[platform] = {"prompt": prompt, "image_path": None}

    return results


def _generate_with_fal(prompt: str, specs: dict, platform: str, output_dir: Path, fal_key: str) -> Path | None:
    try:
        import fal_client

        def _on_queue_update(update):
            pass

        result = fal_client.subscribe(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": {"width": specs["width"], "height": specs["height"]},
                "num_inference_steps": 4,
                "num_images": 1,
            },
            with_logs=False,
            on_queue_update=_on_queue_update,
        )

        image_url = result["images"][0]["url"]
        resp = requests.get(image_url, timeout=30)
        resp.raise_for_status()

        image_path = output_dir / f"{platform}.png"
        image_path.write_bytes(resp.content)
        print(f"[image_generator] Image saved: {image_path}")
        return image_path

    except Exception as e:
        print(f"[image_generator] Error generating image for {platform}: {e}")
        return None
