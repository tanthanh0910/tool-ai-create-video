"""
Video Splitter - Tải video từ URL hoặc đọc file local, cắt thành nhiều đoạn ngắn.
Dùng ffmpeg để xử lý nhanh (không re-encode).
"""

import asyncio
import glob
import os
import subprocess
import json
from config import Config


def get_video_duration(video_path: str) -> float | None:
    """Lấy thời lượng video bằng ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (json.JSONDecodeError, KeyError):
        print(f"  [!] Not a valid video file")
        return None


def split_video_by_duration(
    video_path: str,
    segment_seconds: int,
    output_dir: str,
) -> list[str]:
    """Cắt video thành nhiều đoạn theo thời lượng cố định."""
    os.makedirs(output_dir, exist_ok=True)
    duration = get_video_duration(video_path)
    if duration is None:
        return []

    segments = []
    start = 0.0
    index = 1

    while start < duration:
        end = min(start + segment_seconds, duration)
        if end - start < 2:
            break

        output_path = os.path.join(output_dir, f"part_{index:03d}.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(segment_seconds),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            segments.append(output_path)

        start = end
        index += 1

    return segments


def split_video_by_count(
    video_path: str,
    num_parts: int,
    output_dir: str,
) -> list[str]:
    """Cắt video thành N phần bằng nhau."""
    duration = get_video_duration(video_path)
    if duration is None:
        return []
    segment_seconds = int(duration / num_parts)
    if segment_seconds < 2:
        segment_seconds = 2
    return split_video_by_duration(video_path, segment_seconds, output_dir)


async def download_video(url: str, output_dir: str) -> str | None:
    """Tải video từ URL bằng yt-dlp."""
    try:
        output_template = os.path.join(output_dir, "downloaded.%(ext)s")

        cmd = [
            "yt-dlp",
            "-f", "best[ext=mp4]/best",
            "-o", output_template,
            "--no-playlist",
            "--no-overwrites",
            "--remote-components", "ejs:github",
            url,
        ]

        print(f"  Running yt-dlp...")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        out_text = stdout.decode().strip()
        err_text = stderr.decode().strip()

        if proc.returncode != 0:
            print(f"  [!] yt-dlp error (code {proc.returncode}):")
            print(f"  stdout: {out_text[:300]}")
            print(f"  stderr: {err_text[:300]}")
            return None

        if err_text:
            print(f"  [yt-dlp warnings]: {err_text[:200]}")

        # Tìm file đã tải (yt-dlp có thể thêm extension khác)
        downloaded = glob.glob(os.path.join(output_dir, "downloaded.*"))
        # Loc bo file .part (dang tai do)
        downloaded = [f for f in downloaded if not f.endswith(".part")]
        if downloaded:
            path = downloaded[0]
            size_mb = os.path.getsize(path) / 1024 / 1024
            if size_mb > 0.1:
                print(f"  Downloaded: {path} ({size_mb:.1f} MB)")
                return path
            else:
                print(f"  [!] Downloaded file too small ({size_mb:.2f} MB)")
                return None

        print(f"  [!] No downloaded file found in {output_dir}")
        print(f"  Files in dir: {os.listdir(output_dir)}")
        return None

    except FileNotFoundError:
        print("  [!] yt-dlp not found. Install: pip install yt-dlp")
        return None
    except Exception as e:
        print(f"  [!] Download error: {e}")
        return None


async def split_pipeline(
    source: str,
    num_parts: int | None = None,
    segment_seconds: int | None = None,
) -> list[str]:
    """
    Pipeline cắt video:
    - source: URL hoặc đường dẫn file local
    - num_parts: cắt thành N phần (ưu tiên)
    - segment_seconds: hoặc cắt theo giây (mặc định 60s)
    """
    output_dir = os.path.join(Config.OUTPUT_DIR, "splits")
    os.makedirs(output_dir, exist_ok=True)
    temp_dir = Config.TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)

    is_url = source.startswith("http://") or source.startswith("https://")

    if is_url:
        print(f"  Downloading video...")
        video_path = await download_video(source, temp_dir)
        if not video_path:
            print("  [!] Download failed. Check URL and try again.")
            return []
        size_mb = os.path.getsize(video_path) / 1024 / 1024
        print(f"  Downloaded: {size_mb:.1f} MB -> {video_path}")
    else:
        video_path = os.path.expanduser(source)
        if not os.path.exists(video_path):
            print(f"  [!] File not found: {video_path}")
            return []

    # Validate video
    duration = get_video_duration(video_path)
    if duration is None:
        print("  [!] Cannot read video. File may be corrupted or not a video.")
        return []

    print(f"  Video duration: {duration:.1f}s ({duration/60:.1f} min)")

    # Cắt video
    if num_parts:
        print(f"  Splitting into {num_parts} parts...")
        segments = split_video_by_count(video_path, num_parts, output_dir)
    else:
        seg_sec = segment_seconds or 60
        print(f"  Splitting every {seg_sec}s...")
        segments = split_video_by_duration(video_path, seg_sec, output_dir)

    return segments
