"""
Video Assembler - Ghép ảnh + audio thành video bằng MoviePy v2.
"""

import os
from moviepy import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
    vfx,
)
from config import Config


def create_video_from_scenes(
    image_paths: list[str],
    audio_paths: list[str],
    output_path: str,
    title: str = "",
) -> str | None:
    """Ghép ảnh + audio thành 1 video hoàn chỉnh."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        clips = []

        for img_path, audio_path in zip(image_paths, audio_paths):
            if not os.path.exists(img_path) or not os.path.exists(audio_path):
                continue

            audio = AudioFileClip(audio_path)
            duration = max(audio.duration, Config.SECONDS_PER_IMAGE)

            clip = (
                ImageClip(img_path, duration=duration)
                .resized((Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT))
                .with_audio(audio)
                .with_effects([
                    vfx.FadeIn(0.5),
                    vfx.FadeOut(0.5),
                ])
            )
            clips.append(clip)

        if not clips:
            print(f"  [!] No valid clips for: {title}")
            return None

        final = concatenate_videoclips(clips)
        final.write_videofile(
            output_path,
            fps=Config.FPS,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="ultrafast",
            logger=None,
        )

        # Cleanup
        for clip in clips:
            clip.close()
        final.close()

        return output_path

    except Exception as e:
        print(f"  [!] Video assembly error: {e}")
        return None
