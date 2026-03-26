"""
Video Summarizer - Tom tat video dai thanh video ngan.

Flow:
1. Tai video (yt-dlp)
2. Trich xuat audio (ffmpeg)
3. Chuyen audio thanh text co timestamp (faster-whisper)
4. Ollama phan tich transcript, chon cac doan quan trong
5. Cat cac doan tu video goc va ghep lai (ffmpeg)
"""

import asyncio
import json
import os
import subprocess
from config import Config
from generators.video_splitter import download_video, get_video_duration


def extract_audio(video_path: str, audio_path: str) -> str | None:
    """Trich xuat audio tu video bang ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(audio_path):
        return audio_path
    return None


def transcribe_audio(audio_path: str, log_fn=None) -> list[dict]:
    """
    Chuyen audio thanh text co timestamp bang faster-whisper.
    Tra ve list: [{"start": 0.0, "end": 5.2, "text": "..."}, ...]
    """
    from faster_whisper import WhisperModel

    if log_fn:
        log_fn("Dang tai model Whisper (lan dau mat vai phut)...")

    model = WhisperModel("base", device="cpu", compute_type="int8")

    if log_fn:
        log_fn("Dang chuyen giong noi thanh van ban...")

    segments, info = model.transcribe(audio_path, language=None)

    if log_fn:
        log_fn(f"Ngon ngu phat hien: {info.language} (do tin cay: {info.language_probability:.0%})")

    transcript = []
    for seg in segments:
        transcript.append({
            "start": round(seg.start, 1),
            "end": round(seg.end, 1),
            "text": seg.text.strip(),
        })

    return transcript


def format_timestamp(seconds: float) -> str:
    """Chuyen so giay thanh MM:SS."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def select_key_segments(
    transcript: list[dict],
    video_duration: float,
    target_duration: int = 1200,
    log_fn=None,
) -> list[dict]:
    """
    Dung Ollama de chon cac doan quan trong tu transcript.
    Tra ve list: [{"start": 10.0, "end": 45.0, "reason": "..."}, ...]
    """
    # Gom transcript thanh cac khoi 30 giay de giam token
    chunks = []
    current_chunk = {"start": 0, "end": 0, "text": ""}
    for seg in transcript:
        if seg["start"] - current_chunk["start"] > 30 and current_chunk["text"]:
            chunks.append(current_chunk.copy())
            current_chunk = {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
        else:
            current_chunk["end"] = seg["end"]
            current_chunk["text"] += " " + seg["text"]

    if current_chunk["text"]:
        chunks.append(current_chunk)

    # Tao transcript text co timestamp
    transcript_text = ""
    for c in chunks:
        ts = format_timestamp(c["start"])
        transcript_text += f"[{ts}] {c['text'].strip()}\n"

    target_min = target_duration // 60

    prompt = f"""Ban la chuyen gia tom tat video. Duoi day la transcript cua 1 video review phim dai {video_duration/60:.0f} phut.

Hay chon cac doan QUAN TRONG NHAT de tao 1 video tom tat dai khoang {target_min} phut.

QUY TAC:
- Chon cac doan co noi dung chinh: gioi thieu phim, phan tich nhan vat, cao trao, ket luan
- Bo cac doan lan man, quang cao, noi chuyen linh tinh
- Tong thoi luong cac doan duoc chon phai gan {target_min} phut
- Giu thu tu thoi gian tu dau den cuoi
- Moi doan nen dai it nhat 15 giay

Tra ve JSON thuan (KHONG markdown):
{{"segments": [{{"start": 0, "end": 45, "reason": "Gioi thieu phim"}}]}}

TRANSCRIPT:
{transcript_text}
"""

    if log_fn:
        log_fn(f"Dang phan tich {len(chunks)} doan voi Ollama...")

    import requests
    response = requests.post(
        f"{Config.OLLAMA_URL}/api/generate",
        json={
            "model": Config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 4000},
        },
        timeout=300,
    )
    response.raise_for_status()
    response_text = response.json()["response"]

    # Parse JSON - bracket matching
    start = response_text.find("{")
    if start == -1:
        raise ValueError("Khong tim thay JSON trong response")
    depth = 0
    in_string = False
    escape = False
    end = start
    for i in range(start, len(response_text)):
        c = response_text[i]
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
                end = i + 1
                break

    data = json.loads(response_text[start:end])
    segments = data.get("segments", [])

    # Tinh tong thoi luong
    total = sum(s["end"] - s["start"] for s in segments)
    if log_fn:
        log_fn(f"Da chon {len(segments)} doan, tong: {total/60:.1f} phut")

    return segments


def cut_and_join_segments(
    video_path: str,
    segments: list[dict],
    output_path: str,
    log_fn=None,
) -> str | None:
    """Cat cac doan tu video goc va ghep lai thanh 1 video moi."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_dir = os.path.join(Config.TEMP_DIR, "summary_parts")
    os.makedirs(temp_dir, exist_ok=True)

    part_files = []
    for i, seg in enumerate(segments):
        part_path = os.path.join(temp_dir, f"part_{i:03d}.mp4")
        duration = seg["end"] - seg["start"]

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(seg["start"]),
            "-i", video_path,
            "-t", str(duration),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            part_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True)

        if os.path.exists(part_path) and os.path.getsize(part_path) > 1000:
            part_files.append(part_path)
            if log_fn:
                reason = seg.get("reason", "")
                log_fn(f"  Doan {i+1}: {format_timestamp(seg['start'])}-{format_timestamp(seg['end'])} ({reason})")

    if not part_files:
        return None

    # Tao file list cho ffmpeg concat
    list_path = os.path.join(temp_dir, "filelist.txt")
    with open(list_path, "w") as f:
        for p in part_files:
            f.write(f"file '{p}'\n")

    # Ghep bang ffmpeg concat
    if log_fn:
        log_fn(f"Dang ghep {len(part_files)} doan thanh video tom tat...")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0 and os.path.exists(output_path):
        return output_path
    return None


async def summarize_pipeline(
    source: str,
    target_minutes: int = 20,
    log_fn=None,
) -> str | None:
    """
    Pipeline tom tat video:
    1. Tai video
    2. Trich xuat audio
    3. Transcribe (Whisper)
    4. Chon doan quan trong (Ollama)
    5. Cat + ghep video
    """
    _log = log_fn or print
    target_seconds = target_minutes * 60

    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)

    # 1. Tai hoac doc video
    is_url = source.startswith("http://") or source.startswith("https://")
    if is_url:
        _log("Dang tai video...")
        video_path = await download_video(source, Config.TEMP_DIR)
        if not video_path:
            _log("Tai video that bai!")
            return None
        size_mb = os.path.getsize(video_path) / 1024 / 1024
        _log(f"Da tai: {size_mb:.1f} MB")
    else:
        video_path = os.path.expanduser(source)
        if not os.path.exists(video_path):
            _log(f"File khong ton tai: {video_path}")
            return None

    # Kiem tra duration
    duration = get_video_duration(video_path)
    if not duration:
        _log("Khong doc duoc video!")
        return None
    _log(f"Video goc: {duration/60:.1f} phut")

    if duration <= target_seconds:
        _log(f"Video da ngan hon {target_minutes} phut, khong can tom tat.")
        return None

    # 2. Trich xuat audio
    _log("Dang trich xuat audio...")
    audio_path = os.path.join(Config.TEMP_DIR, "summary_audio.wav")
    if not extract_audio(video_path, audio_path):
        _log("Trich xuat audio that bai!")
        return None

    # 3. Transcribe
    transcript = transcribe_audio(audio_path, log_fn=_log)
    _log(f"Da chuyen thanh {len(transcript)} doan text")

    if not transcript:
        _log("Khong nhan dien duoc loi noi trong video!")
        return None

    # 4. Chon doan quan trong
    segments = select_key_segments(transcript, duration, target_seconds, log_fn=_log)
    if not segments:
        _log("Khong chon duoc doan nao!")
        return None

    # 5. Cat + ghep
    output_path = os.path.join(Config.OUTPUT_DIR, "summary.mp4")
    result = cut_and_join_segments(video_path, segments, output_path, log_fn=_log)

    if result:
        final_duration = get_video_duration(result)
        if final_duration:
            _log(f"Video tom tat: {final_duration/60:.1f} phut (tu {duration/60:.1f} phut)")
    return result
