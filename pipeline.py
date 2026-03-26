"""
Pipeline - Điều phối toàn bộ quy trình tạo nhiều video song song.
"""

import asyncio
import os
import shutil
import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from config import Config
from generators.script_generator import generate_scripts
from generators.image_generator import generate_images_for_scenes
from generators.audio_generator import generate_audios_for_scenes
from generators.video_assembler import create_video_from_scenes

console = Console()


async def process_single_video(
    video_script: dict, video_index: int, total: int
) -> str | None:
    """Xử lý 1 video: tạo ảnh + audio song song, rồi ghép thành video."""
    title = video_script["title"]
    scenes = video_script["scenes"]
    video_dir = os.path.join(Config.TEMP_DIR, f"video_{video_index:03d}")
    os.makedirs(video_dir, exist_ok=True)

    console.print(
        f"\n  [{video_index + 1}/{total}] [bold cyan]{title}[/] "
        f"({len(scenes)} scenes)"
    )

    # Tạo ảnh và audio SONG SONG cho từng video
    console.print("    Creating images + audio in parallel...")
    image_results, audio_results = await asyncio.gather(
        generate_images_for_scenes(scenes, video_dir),
        generate_audios_for_scenes(scenes, video_dir),
    )

    image_paths = [r for r in image_results if r is not None]
    audio_paths = [r for r in audio_results if r is not None]

    if not image_paths or not audio_paths:
        console.print(f"    [red]Failed - missing images or audio[/]")
        return None

    # Ghép video
    safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
    output_path = os.path.join(
        Config.OUTPUT_DIR, f"{video_index + 1:02d}_{safe_title[:50]}.mp4"
    )

    console.print("    Assembling video...")
    result = await asyncio.to_thread(
        create_video_from_scenes, image_paths, audio_paths, output_path, title
    )

    if result:
        console.print(f"    [green]Done -> {output_path}[/]")
    else:
        console.print(f"    [red]Failed to assemble video[/]")

    return result


async def run_pipeline(user_prompt: str, num_videos: int = 5) -> list[str]:
    """Chạy toàn bộ pipeline: tạo kịch bản -> tạo video song song."""
    start_time = time.time()

    # Setup directories
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(Config.TEMP_DIR, exist_ok=True)

    # Step 1: Tạo kịch bản bằng Ollama
    console.print("\n[bold yellow]Step 1:[/] Generating scripts with Ollama...")
    try:
        scripts = generate_scripts(user_prompt, num_videos)
        console.print(f"  Created {len(scripts)} video scripts")
    except Exception as e:
        console.print(f"  [red]Script generation failed: {e}[/]")
        console.print(
            "  [dim]Make sure Ollama is running: ollama serve[/]"
        )
        return []

    # Step 2: Tạo video tuần tự (Pollinations.ai free không chịu được concurrent)
    console.print(
        f"\n[bold yellow]Step 2:[/] Generating {len(scripts)} videos sequentially..."
    )

    total = len(scripts)
    results = []
    for i, script in enumerate(scripts):
        result = await process_single_video(script, i, total)
        results.append(result)

    # Cleanup temp
    if os.path.exists(Config.TEMP_DIR):
        shutil.rmtree(Config.TEMP_DIR)

    # Summary
    successful = [r for r in results if r is not None]
    elapsed = time.time() - start_time

    console.print(f"\n[bold green]{'=' * 50}[/]")
    console.print(
        f"[bold]Completed: {len(successful)}/{total} videos "
        f"in {elapsed:.1f}s[/]"
    )
    for path in successful:
        console.print(f"  -> {path}")
    console.print(f"[bold green]{'=' * 50}[/]\n")

    return successful
