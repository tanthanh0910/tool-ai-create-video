"""
Video Remake - Xem video goc, phan tich HINH ANH + NOI DUNG, tao video tuong tu.

Flow:
1. Tai video goc (yt-dlp)
2. Trich xuat keyframes -> AI mo ta tung frame (HuggingFace image-to-text)
3. Trich xuat audio -> transcribe (Whisper)
4. Ket hop mo ta hinh + transcript -> Ollama tao kich ban TUONG TU
5. Tao hinh anh moi (HuggingFace) dua tren mo ta tu video goc
6. Tao loi ke moi (Edge TTS)
7. Ghep nhac nen + xuat video
"""

import asyncio
import base64
import json
import os
import subprocess
import requests
import aiohttp
from config import Config


def extract_keyframes(video_path: str, output_dir: str, num_frames: int = 10) -> list[dict]:
    """
    Trich xuat keyframes tu video (chat luong cao de dung lam hinh trong video moi).
    Tra ve: [{"path": "/path/frame.jpg", "timestamp": 12.5}, ...]
    """
    os.makedirs(output_dir, exist_ok=True)
    duration = _get_duration(video_path)
    if not duration:
        return []

    interval = duration / (num_frames + 1)
    frames = []
    for i in range(num_frames):
        timestamp = interval * (i + 1)
        output_path = os.path.join(output_dir, f"frame_{i:03d}.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "1",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(output_path):
            frames.append({"path": output_path, "timestamp": timestamp})
    return frames


def extract_scene_clips(video_path: str, output_dir: str, num_scenes: int = 6) -> list[dict]:
    """
    Cat video goc thanh nhieu doan ngan (scene clips) de dung trong video moi.
    Tra ve: [{"path": "/path/clip.mp4", "start": 0, "end": 30, "frame_path": "/path/frame.jpg"}, ...]
    """
    os.makedirs(output_dir, exist_ok=True)
    duration = _get_duration(video_path)
    if not duration:
        return []

    scene_duration = duration / num_scenes
    clips = []
    for i in range(num_scenes):
        start = i * scene_duration
        end = min((i + 1) * scene_duration, duration)

        # Trich xuat 1 frame dai dien (o giua doan)
        mid = (start + end) / 2
        frame_path = os.path.join(output_dir, f"scene_{i:03d}.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(mid),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "1",
            frame_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True)

        clips.append({
            "frame_path": frame_path if os.path.exists(frame_path) else None,
            "start": start,
            "end": end,
            "timestamp": mid,
        })
    return clips


def describe_frame(image_path: str) -> str | None:
    """Dung Ollama LLaVA (vision model, chay local) de mo ta 1 frame."""
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        response = requests.post(
            f"{Config.OLLAMA_URL}/api/generate",
            json={
                "model": "llava:7b",
                "prompt": (
                    "Describe this image in detail in English. "
                    "Include: characters (appearance, clothing, expression), "
                    "background (location, lighting, colors), "
                    "and actions happening. Be specific and concise (2-3 sentences)."
                ),
                "images": [image_data],
                "stream": False,
                "options": {"num_predict": 200},
            },
            timeout=120,
        )
        if response.status_code == 200:
            text = response.json().get("response", "").strip()
            return text if text else None
        return None
    except Exception as e:
        print(f"  [!] Frame description error: {e}")
        return None


def _get_duration(video_path: str) -> float | None:
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (json.JSONDecodeError, KeyError):
        return None


def format_ts(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def analyze_and_create_script(
    transcript: list[dict],
    frame_descriptions: list[dict],
    video_duration: float,
    num_scenes: int = 6,
) -> dict:
    """
    Ket hop transcript + mo ta hinh anh de tao kich ban TUONG TU video goc.
    """
    # Gom transcript
    transcript_text = ""
    for seg in transcript:
        transcript_text += f"{seg['text']} "
    transcript_text = transcript_text[:3000]

    # Gom frame descriptions
    frames_text = ""
    for fd in frame_descriptions:
        ts = format_ts(fd["timestamp"])
        desc = fd.get("description", "unknown")
        frames_text += f"[{ts}] {desc}\n"

    prompt = f"""Ban la chuyen gia lam lai video. Duoi day la NOI DUNG va MO TA HINH ANH cua video goc.

=== MO TA HINH ANH TU VIDEO GOC ===
{frames_text}

=== LOI THOAI / LOI KE TRONG VIDEO GOC ===
{transcript_text}

=== NHIEM VU ===
Viet lai loi ke cho video. Video moi se DUNG LAI HINH ANH GOC nen loi ke phai SAT voi nhung gi dang xay ra trong video.

YEU CAU:
- Viet {num_scenes} doan loi ke (narration) tieng Viet
- Moi doan 2-4 cau, tuong ung voi 1 phan cua video goc theo DUNG thu tu
- Noi dung GIONG 80-85% video goc: CUNG cot truyen, CUNG su kien, CUNG nhan vat
- Chi DIEN DAT LAI (paraphrase) bang cach noi khac, KHONG sao chep nguyen van
- Giu giong ke chuyen hap dan, truyen cam
- Neu video goc co giai thich/phan tich, giu lai y chinh

CHI tra ve JSON, KHONG viet gi khac, KHONG markdown, KHONG giai thich truoc hay sau JSON:
{{
  "title": "Tieu de tieng Viet (gan giong video goc)",
  "scenes": [
    {{
      "narration": "Loi ke tieng Viet 2-4 cau - viet lai noi dung video goc bang cach dien dat khac"
    }},
    {{
      "narration": "Doan tiep theo..."
    }}
  ]
}}

QUAN TRONG: Phai co DUNG {num_scenes} phan tu trong mang scenes. Chi tra ve JSON thuan.
"""

    response = requests.post(
        f"{Config.OLLAMA_URL}/api/generate",
        json={
            "model": Config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.5, "num_predict": 6000},
        },
        timeout=300,
    )
    response.raise_for_status()
    response_text = response.json()["response"]

    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    try:
        return json.loads(_extract_json(response_text))
    except (ValueError, json.JSONDecodeError) as e:
        print(f"  [!] Ollama response (khong parse duoc JSON):\n{response_text[:500]}")
        raise ValueError(f"{e} | Response: {response_text[:200]}")


def _extract_json(text: str) -> str:
    """Trich xuat JSON object dau tien tu text bang bracket matching."""
    start = text.find("{")
    if start == -1:
        raise ValueError("Khong tim thay JSON trong response")
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == '\\' and in_string:
            escape = True
            continue
        if c == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text[start:]


async def download_free_music(output_path: str, duration_seconds: float) -> str | None:
    """Tao nhac nen ambient bang ffmpeg."""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=220:duration={int(duration_seconds)}",
            "-f", "lavfi",
            "-i", f"sine=frequency=330:duration={int(duration_seconds)}",
            "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={int(duration_seconds)}",
            "-filter_complex",
            "[0]volume=0.05[a];[1]volume=0.03[b];[2]volume=0.02[c];"
            "[a][b][c]amix=inputs=3:duration=longest,"
            "atempo=0.8,aecho=0.8:0.88:60:0.4,"
            "lowpass=f=800,highpass=f=80",
            "-t", str(int(duration_seconds)),
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
        return None
    except Exception as e:
        print(f"  [!] Music generation error: {e}")
        return None
