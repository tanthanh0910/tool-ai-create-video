#!/usr/bin/env python3
"""
Web UI server cho AI Video Tool.
Chay: python app.py
Mo trinh duyet: http://localhost:5000
"""

import asyncio
import json
import os
import shutil
from flask import Flask, render_template, request, Response, send_file

from config import Config
from generators.script_generator import generate_scripts
from generators.video_assembler import create_video_from_scenes
from generators.animal_video_generator import (
    generate_animal_scripts,
    PEXELS_API_KEY,
)

app = Flask(__name__)


# ---------- Helpers ----------

def run_async(coro):
    """Chay async function trong Flask thread (sync)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def log_event(msg: str, level: str = "info") -> str:
    return sse_event({"type": "log", "message": msg, "level": level})


def progress_event(percent: float) -> str:
    return sse_event({"type": "progress", "percent": min(percent, 100)})


def done_event(msg: str, files: list[str]) -> str:
    return sse_event({"type": "done", "message": msg, "files": files})


def error_event(msg: str) -> str:
    return sse_event({"type": "error", "message": msg})


# ---------- Routes ----------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download/<path:filepath>")
def download(filepath):
    if os.path.exists(filepath) and filepath.startswith(("./output", "output")):
        return send_file(filepath, as_attachment=True)
    return "File not found", 404


# ---------- API: Generate Videos ----------

@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.json
    prompt = data.get("prompt", "")
    num = data.get("num", 3)
    mode = data.get("mode", "ai")  # "ai" = tạo ảnh AI, "real" = ảnh/video thực
    orientation = data.get("orientation", "landscape")  # "landscape", "portrait", "square"
    animals_per_video = data.get("animals_per_video", 10)  # Số động vật mỗi video

    # Nếu mode = "real" hoặc prompt liên quan đến động vật -> dùng animal generator
    animal_keywords = ["animal", "động vật", "con vật", "wildlife", "thú", "chim", "cá"]
    is_animal_topic = any(kw in prompt.lower() for kw in animal_keywords) or mode == "real"
    
    if is_animal_topic and PEXELS_API_KEY:
        return api_generate_animal_video(prompt, num, orientation, animals_per_video)
    
    # Original AI generation flow
    def generate_stream():
        yield log_event(f"Bat dau tao {num} video voi chu de: {prompt}")
        yield progress_event(5)

        # Step 1: Scripts
        yield log_event("Dang tao kich ban bang Ollama...")
        try:
            scripts = generate_scripts(prompt, num)
            yield log_event(f"Da tao {len(scripts)} kich ban", "success")
            yield progress_event(15)
        except Exception as e:
            yield error_event(f"Loi tao kich ban: {e}")
            yield log_event("Dam bao Ollama dang chay: ollama serve", "warn")
            return

        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        os.makedirs(Config.TEMP_DIR, exist_ok=True)
        total = len(scripts)
        completed_files = []

        # Step 2: Process each video
        for i, script in enumerate(scripts):
            title = script["title"]
            scenes = script["scenes"]
            video_dir = os.path.join(Config.TEMP_DIR, f"video_{i:03d}")
            os.makedirs(video_dir, exist_ok=True)

            yield log_event(f"[{i+1}/{total}] {title} ({len(scenes)} canh)")
            base_pct = 15 + (i / total) * 75

            # Generate images tung cai (de co log)
            from generators.image_generator import generate_image
            from generators.audio_generator import generate_audio as gen_audio
            images = []
            for si, scene in enumerate(scenes):
                yield log_event(f"  Hinh {si+1}/{len(scenes)}...")
                img_path = os.path.join(video_dir, f"scene_{si:03d}.png")
                enhanced = (
                    f"{scene['image_prompt']}, "
                    "masterpiece, best quality, ultra detailed, sharp focus, "
                    "professional illustration, vivid colors, cinematic composition"
                )
                r = run_async(generate_image(enhanced, img_path))
                if r:
                    images.append(r)
                    yield log_event(f"  Hinh {si+1} OK", "success")
                else:
                    yield log_event(f"  Hinh {si+1} that bai", "error")

            # Generate audio tung cai
            audios = []
            for si, scene in enumerate(scenes):
                yield log_event(f"  Audio {si+1}/{len(scenes)}...")
                aud_path = os.path.join(video_dir, f"narration_{si:03d}.mp3")
                r = run_async(gen_audio(scene["narration"], aud_path))
                if r:
                    audios.append(r)
                    yield log_event(f"  Audio {si+1} OK", "success")
                else:
                    yield log_event(f"  Audio {si+1} that bai", "error")

            yield progress_event(base_pct + 35 / total)

            if not images or not audios:
                yield log_event(f"  Khong du anh/audio, bo qua video nay", "error")
                continue

            # Assemble video
            yield log_event(f"  Dang ghep video...")
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
            output_path = os.path.join(Config.OUTPUT_DIR, f"{i+1:02d}_{safe_title[:50]}.mp4")

            result = create_video_from_scenes(images, audios, output_path, title)
            yield progress_event(base_pct + 75 / total)

            if result:
                completed_files.append(result)
                yield log_event(f"  Hoan thanh: {result}", "success")
            else:
                yield log_event(f"  Ghep video that bai", "error")

        # Cleanup
        if os.path.exists(Config.TEMP_DIR):
            shutil.rmtree(Config.TEMP_DIR)

        yield done_event(
            f"Hoan thanh {len(completed_files)}/{total} video!",
            completed_files,
        )

    return Response(generate_stream(), mimetype="text/event-stream")


# ---------- API: Generate Animal Videos (Real Images/Videos) ----------

def api_generate_animal_video(prompt: str, num: int, orientation: str = "landscape", animals_per_video: int = 10):
    """Tạo video động vật với hình ảnh/video thực từ Pexels."""
    
    # Xác định kích thước video dựa trên orientation
    if orientation == "portrait":
        video_width, video_height = 1080, 1920  # 9:16 TikTok/Shorts
        orientation_label = "Doc 9:16"
    elif orientation == "square":
        video_width, video_height = 1080, 1080  # 1:1 Instagram
        orientation_label = "Vuong 1:1"
    else:
        video_width, video_height = 1920, 1080  # 16:9 YouTube
        orientation_label = "Ngang 16:9"
    
    def generate_stream():
        yield log_event(f"🦁 Tao video dong vat voi hinh anh/video THUC")
        yield log_event(f"📐 Kich thuoc: {video_width}x{video_height} ({orientation_label})")
        yield log_event(f"🔢 So dong vat moi video: {animals_per_video}")
        yield log_event(f"Chu de: {prompt}, So video: {num}")
        yield progress_event(5)

        # Check Pexels API key
        if not PEXELS_API_KEY:
            yield error_event("Thieu PEXELS_API_KEY trong file .env")
            yield log_event("Dang ky mien phi tai: https://www.pexels.com/api/", "warn")
            return

        # Kiểm tra xem prompt có phải là danh sách động vật trực tiếp không
        # Ví dụ: "cá heo, lợn biển, rùa biển" hoặc "sư tử, voi, hổ"
        def parse_animal_list(text: str) -> list[str]:
            """Phân tích danh sách động vật từ text."""
            # Tách bởi dấu phẩy hoặc dấu chấm phẩy
            parts = text.replace(";", ",").split(",")
            animals = [p.strip() for p in parts if p.strip()]
            # Nếu có ít nhất 2 phần và mỗi phần ngắn (< 20 ký tự) -> là danh sách
            if len(animals) >= 2 and all(len(a) < 20 for a in animals):
                return animals
            return []
        
        direct_animals = parse_animal_list(prompt)
        
        if direct_animals:
            # Người dùng nhập trực tiếp danh sách động vật
            yield log_event(f"✓ Phat hien danh sach dong vat truc tiep: {len(direct_animals)} con")
            scripts = [{
                "title": f"Video {len(direct_animals)} động vật",
                "theme": "Động vật",
                "animals": direct_animals
            }]
        else:
            # Tạo danh sách động vật random từ database
            # num = số video, animals_per_video = số động vật mỗi video
            yield log_event(f"Dang tao danh sach {num} video, moi video {animals_per_video} dong vat...")
            try:
                scripts = generate_animal_scripts(prompt, num_videos=num, animals_per_video=animals_per_video)
                total_animals = sum(len(s.get("animals", [])) for s in scripts)
                yield log_event(f"Da tao {len(scripts)} video voi tong {total_animals} dong vat", "success")
            except Exception as e:
                yield log_event(f"Loi: {e}", "warn")
                scripts = []
            
            # Fallback nếu không có kết quả
            if not scripts:
                yield log_event(f"Dung danh sach mac dinh {animals_per_video} dong vat", "warn")
                from generators.animal_video_generator import ANIMAL_CATEGORIES
                import random
                all_animals = []
                for cat in ANIMAL_CATEGORIES.values():
                    all_animals.extend(cat["animals"])
                all_animals = list(set(all_animals))
                random.shuffle(all_animals)
                scripts = [{
                    "title": f"Khám phá {animals_per_video} loài động vật",
                    "theme": "mixed",
                    "animals": all_animals[:animals_per_video]
                }]
        
        yield progress_event(15)

        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        
        # XÓA SẠCH temp folder trước khi bắt đầu để tránh nhầm lẫn file cũ
        if os.path.exists(Config.TEMP_DIR):
            shutil.rmtree(Config.TEMP_DIR)
        os.makedirs(Config.TEMP_DIR, exist_ok=True)
        yield log_event("Da xoa sach thu muc temp")
        
        total = len(scripts)
        completed_files = []

        # Step 2: Process each video
        for i, script in enumerate(scripts):
            title = script.get("title", f"Video {i+1}")
            animals = script.get("animals", [])
            
            yield log_event(f"[{i+1}/{total}] {title}")
            yield log_event(f"  Dong vat: {', '.join(animals)}")
            
            base_pct = 15 + (i / total) * 80

            # Tạo thư mục riêng cho mỗi video - xóa cũ nếu có
            import time
            timestamp = int(time.time())
            work_dir = os.path.join(Config.TEMP_DIR, f"video_{i:03d}_{timestamp}")
            
            # Xóa thư mục cũ nếu tồn tại
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir)
            os.makedirs(work_dir, exist_ok=True)
            
            yield log_event(f"  Working dir: {work_dir}")
            
            clips = []
            for ai, animal in enumerate(animals):
                yield log_event(f"  [{ai+1}/{len(animals)}] {animal}...")
                
                # Import function từ animal generator
                from generators.animal_video_generator import create_animal_clip
                
                clip = run_async(create_animal_clip(
                    animal_name=animal,
                    work_dir=work_dir,
                    clip_index=ai,
                    use_video=True,
                    clip_duration=8.0,
                    orientation=orientation,  # Truyền orientation
                    target_width=video_width,
                    target_height=video_height,
                ))
                
                if clip:
                    clips.append((animal, clip))  # Lưu cả tên và đường dẫn
                    yield log_event(f"    ✓ {animal} (doc ten + tieng keu)", "success")
                else:
                    yield log_event(f"    ✗ {animal} that bai", "error")
                
                yield progress_event(base_pct + (ai + 1) / len(animals) * 40 / total)

            if not clips:
                yield log_event(f"  Khong tao duoc clip nao, bo qua video nay", "error")
                continue

            # Ghép các clip lại - LOG THỨ TỰ
            yield log_event(f"  === GHEP {len(clips)} CLIP THEO THU TU ===")
            clip_paths = []
            for idx, (animal_name, clip_path) in enumerate(clips):
                yield log_event(f"    {idx+1}. {animal_name}: {clip_path}")
                clip_paths.append(clip_path)
            
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
            output_path = os.path.join(Config.OUTPUT_DIR, f"{i+1:02d}_{safe_title[:50]}.mp4")
            
            from generators.animal_video_generator import concatenate_videos
            result = concatenate_videos(clip_paths, output_path, video_width, video_height)
            
            yield progress_event(base_pct + 80 / total)

            if result:
                completed_files.append(result)
                yield log_event(f"  ✓ Hoan thanh: {result}", "success")
            else:
                yield log_event(f"  Ghep video that bai", "error")

        # Cleanup - KHÔNG XÓA temp folder để debug
        # if os.path.exists(Config.TEMP_DIR):
        #     shutil.rmtree(Config.TEMP_DIR)
        yield log_event(f"  📁 Temp folder GIU LAI de debug: {Config.TEMP_DIR}")

        yield done_event(
            f"Hoan thanh {len(completed_files)}/{total} video!",
            completed_files,
        )

    return Response(generate_stream(), mimetype="text/event-stream")


# ---------- Main ----------

if __name__ == "__main__":
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
    print("\n  AI Video Tool - Web UI")
    print("  http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
