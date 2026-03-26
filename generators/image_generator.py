"""
Image Generator - Dùng Hugging Face Inference API (miễn phí).
Cần HF_TOKEN từ https://huggingface.co/settings/tokens (free account).
"""

import asyncio
import aiohttp
import os
from config import Config


async def generate_image(prompt: str, output_path: str, max_retries: int = 3) -> str | None:
    """Tạo 1 ảnh từ prompt bằng HuggingFace Inference API (miễn phí)."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    headers = {
        "Authorization": f"Bearer {Config.HF_TOKEN}",
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "width": min(Config.VIDEO_WIDTH, 1024),
            "height": min(Config.VIDEO_HEIGHT, 1024),
        },
    }

    timeout = aiohttp.ClientTimeout(total=180)

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait = 10 * attempt
                print(f"      Retry {attempt}/{max_retries}, waiting {wait}s...")
                await asyncio.sleep(wait)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"https://router.huggingface.co/hf-inference/models/{Config.HF_IMAGE_MODEL}",
                    headers=headers,
                    json=payload,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        if len(data) > 1000:
                            with open(output_path, "wb") as f:
                                f.write(data)
                            return output_path
                        print(f"      Response too small, retrying...")
                    elif resp.status == 503:
                        # Model đang loading
                        body = await resp.json()
                        wait_time = body.get("estimated_time", 20)
                        print(f"      Model loading, waiting {wait_time:.0f}s...")
                        await asyncio.sleep(wait_time)
                    elif resp.status == 429:
                        print(f"      Rate limited, waiting 30s...")
                        await asyncio.sleep(30)
                    else:
                        text = await resp.text()
                        print(f"      HTTP {resp.status}: {text[:100]}")

        except Exception as e:
            print(f"      Error: {e}")

    print(f"  [!] Failed: {os.path.basename(output_path)}")
    return None


async def generate_images_for_scenes(
    scenes: list[dict], video_dir: str
) -> list[str | None]:
    """Tạo ảnh tuần tự để tránh rate limit."""
    results = []
    for i, scene in enumerate(scenes):
        output_path = os.path.join(video_dir, f"scene_{i:03d}.png")
        enhanced_prompt = (
            f"{scene['image_prompt']}, "
            "masterpiece, best quality, ultra detailed, sharp focus, "
            "professional illustration, vivid colors, cinematic composition"
        )
        print(f"    Image {i + 1}/{len(scenes)}...")
        result = await generate_image(enhanced_prompt, output_path)
        results.append(result)
        # Delay nhẹ giữa các request
        await asyncio.sleep(2)
    return results
