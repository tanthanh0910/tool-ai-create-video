"""
Audio Generator - Dùng Edge TTS (miễn phí) để tạo giọng đọc tiếng Việt.
"""

import asyncio
import os
import edge_tts
from config import Config


async def generate_audio(text: str, output_path: str) -> str | None:
    """Tạo file audio từ text bằng Edge TTS."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        communicate = edge_tts.Communicate(
            text=text,
            voice=Config.TTS_VOICE,
            rate=Config.TTS_RATE,
        )
        await communicate.save(output_path)
        return output_path
    except Exception as e:
        print(f"  [!] TTS error: {e}")
        return None


async def generate_audios_for_scenes(scenes: list[dict], video_dir: str) -> list[str]:
    """Tạo audio cho tất cả scenes song song."""
    tasks = []
    for i, scene in enumerate(scenes):
        output_path = os.path.join(video_dir, f"narration_{i:03d}.mp3")
        tasks.append(generate_audio(scene["narration"], output_path))

    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]
