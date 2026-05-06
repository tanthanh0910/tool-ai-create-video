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
import subprocess
import uuid
from flask import Flask, render_template, request, Response, send_file

from config import Config
from generators.script_generator import generate_scripts
from generators.video_assembler import create_video_from_scenes
from generators.animal_video_generator import (
    generate_animal_scripts,
    PEXELS_API_KEY,
)
from generators.plant_video_generator import (
    generate_plant_scripts,
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
    animals_per_video = data.get("animals_per_video", 10)  # Số động vật/thực vật mỗi video
    category = data.get("category", "animal")  # "animal" hoặc "plant"

    # Mode real -> dùng Pexels generator theo category
    if mode == "real" and PEXELS_API_KEY:
        if category == "plant":
            return api_generate_plant_video(prompt, num, orientation, animals_per_video)
        else:
            return api_generate_animal_video(prompt, num, orientation, animals_per_video)

    # Fallback: nếu prompt liên quan động vật
    animal_keywords = ["animal", "động vật", "con vật", "wildlife", "thú", "chim", "cá"]
    is_animal_topic = any(kw in prompt.lower() for kw in animal_keywords)
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
            
            # === INTRO CLIP (dùng file có sẵn) ===
            intro_clip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "intro_clip.mp4")
            if os.path.exists(intro_clip_path):
                yield log_event(f"  [INTRO] ✓ Dung intro co san: {intro_clip_path}", "success")
            else:
                intro_clip_path = None
                yield log_event(f"  [INTRO] Khong tim thay intro, bo qua")

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
            clip_paths = []

            # Chèn intro clip vào đầu
            if intro_clip_path:
                clip_paths.append(intro_clip_path)
                yield log_event(f"  === GHEP INTRO + {len(clips)} CLIP THEO THU TU ===")
                yield log_event(f"    0. [INTRO]: {intro_clip_path}")
            else:
                yield log_event(f"  === GHEP {len(clips)} CLIP THEO THU TU ===")

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


# ---------- API: Generate Plant Videos ----------

def api_generate_plant_video(prompt: str, num: int, orientation: str = "landscape", plants_per_video: int = 10):
    """Tạo video thực vật với hình ảnh thực từ Pexels + nhạc nền."""

    if orientation == "portrait":
        video_width, video_height = 1080, 1920
        orientation_label = "Doc 9:16"
    elif orientation == "square":
        video_width, video_height = 1080, 1080
        orientation_label = "Vuong 1:1"
    else:
        video_width, video_height = 1920, 1080
        orientation_label = "Ngang 16:9"

    def generate_stream():
        yield log_event(f"🌿 Tao video thuc vat voi hinh anh THUC")
        yield log_event(f"📐 Kich thuoc: {video_width}x{video_height} ({orientation_label})")
        yield log_event(f"🔢 So thuc vat moi video: {plants_per_video}")
        yield progress_event(5)

        if not PEXELS_API_KEY:
            yield error_event("Thieu PEXELS_API_KEY trong file .env")
            return

        # Parse danh sách trực tiếp hoặc random
        def parse_plant_list(text: str) -> list[str]:
            parts = text.replace(";", ",").split(",")
            plants = [p.strip() for p in parts if p.strip()]
            if len(plants) >= 2 and all(len(p) < 30 for p in plants):
                return plants
            return []

        direct_plants = parse_plant_list(prompt)

        if direct_plants:
            yield log_event(f"✓ Danh sach thuc vat truc tiep: {len(direct_plants)} loai")
            scripts = [{
                "title": f"Video {len(direct_plants)} thuc vat",
                "theme": "plants",
                "plants": direct_plants,
            }]
        else:
            yield log_event(f"Dang tao danh sach {num} video, moi video {plants_per_video} thuc vat...")
            scripts = generate_plant_scripts(prompt, num_videos=num, plants_per_video=plants_per_video)
            if not scripts:
                yield log_event("Khong tao duoc danh sach", "error")
                return

        yield progress_event(15)
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        if os.path.exists(Config.TEMP_DIR):
            shutil.rmtree(Config.TEMP_DIR)
        os.makedirs(Config.TEMP_DIR, exist_ok=True)

        total = len(scripts)
        completed_files = []

        for i, script in enumerate(scripts):
            title = script.get("title", f"Video {i+1}")
            plants = script.get("plants", [])

            yield log_event(f"[{i+1}/{total}] {title}")
            yield log_event(f"  Thuc vat: {', '.join(plants)}")

            base_pct = 15 + (i / total) * 80
            import time
            work_dir = os.path.join(Config.TEMP_DIR, f"video_{i:03d}_{int(time.time())}")
            os.makedirs(work_dir, exist_ok=True)

            # Intro clip
            intro_clip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "intro_clip.mp4")
            if not os.path.exists(intro_clip_path):
                intro_clip_path = None

            # Tạo clips
            clips = []
            from generators.plant_video_generator import create_plant_clip
            for pi, plant in enumerate(plants):
                yield log_event(f"  [{pi+1}/{len(plants)}] {plant}...")
                clip = run_async(create_plant_clip(
                    plant_name=plant,
                    work_dir=work_dir,
                    clip_index=pi,
                    use_video=True,
                    clip_duration=6.0,
                    orientation=orientation,
                    target_width=video_width,
                    target_height=video_height,
                    is_first_clip=(pi == 0),
                ))
                if clip:
                    clips.append((plant, clip))
                    yield log_event(f"    ✓ {plant}", "success")
                else:
                    yield log_event(f"    ✗ {plant}", "error")
                yield progress_event(base_pct + (pi + 1) / len(plants) * 40 / total)

            if not clips:
                yield log_event("  Khong tao duoc clip nao", "error")
                continue

            # Ghép clips
            clip_paths = []
            if intro_clip_path:
                clip_paths.append(intro_clip_path)
            for idx, (name, path) in enumerate(clips):
                clip_paths.append(path)

            safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
            concat_path = os.path.join(work_dir, f"concat_{safe_title[:50]}.mp4")

            from generators.animal_video_generator import concatenate_videos
            concat_result = concatenate_videos(clip_paths, concat_path, video_width, video_height)

            if not concat_result:
                yield log_event("  Ghep video that bai", "error")
                continue

            # Thêm nhạc nền
            yield log_event("  🎵 Dang them nhac nen...")
            output_path = os.path.join(Config.OUTPUT_DIR, f"{i+1:02d}_{safe_title[:50]}.mp4")
            from generators.plant_video_generator import add_background_music
            final = add_background_music(concat_result, output_path)

            if final:
                completed_files.append(final)
                yield log_event(f"  ✓ Hoan thanh: {final}", "success")
            else:
                # Fallback: dùng video không nhạc nền
                import shutil as sh
                sh.copy2(concat_result, output_path)
                completed_files.append(output_path)
                yield log_event(f"  ✓ Hoan thanh (khong nhac nen): {output_path}", "success")

            yield progress_event(base_pct + 80 / total)

        yield log_event(f"  📁 Temp folder GIU LAI de debug: {Config.TEMP_DIR}")
        yield done_event(f"Hoan thanh {len(completed_files)}/{total} video!", completed_files)

    return Response(generate_stream(), mimetype="text/event-stream")



# ---------- Multi Merge ----------

@app.route("/api/multi-merge", methods=["POST"])
def api_multi_merge():
    """Ghép nhiều video lại với nhau + audio."""

    # Validate inputs
    video_files = request.files.getlist('videos')
    durations = request.form.getlist('durations')
    audio_file = request.files.get('audio')

    if not video_files or len(video_files) == 0:
        def error_stream():
            yield error_event("Vui long chon it nhat 1 video!")
        return Response(error_stream(), mimetype="text/event-stream")

    if not audio_file or not audio_file.filename:
        def error_stream():
            yield error_event("Vui long chon audio!")
        return Response(error_stream(), mimetype="text/event-stream")

    # Parse effects
    effects_str = request.form.get('effects', '')
    effects = [e.strip() for e in effects_str.split(',') if e.strip()] if effects_str else []

    # Save files
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    unique_id = uuid.uuid4().hex[:8]

    # Ghép video và duration theo cặp (tránh lệch index)
    temp_videos = []
    pair_idx = 0
    for vf in video_files:
        if not vf.filename:
            continue
        ext = os.path.splitext(vf.filename)[1].lower()
        temp_path = os.path.join(Config.TEMP_DIR, f"multi_video_{unique_id}_{pair_idx}{ext}")
        vf.save(temp_path)
        dur = 0
        if pair_idx < len(durations):
            dur_str = durations[pair_idx].strip()
            if dur_str and dur_str != '0':
                try:
                    dur = int(dur_str)
                except ValueError:
                    dur = 0
        temp_videos.append((temp_path, vf.filename, dur))
        pair_idx += 1

    audio_ext = os.path.splitext(audio_file.filename)[1].lower()
    temp_audio = os.path.join(Config.TEMP_DIR, f"multi_audio_{unique_id}{audio_ext}")
    audio_file.save(temp_audio)

    def cleanup_files():
        for tv, _, _ in temp_videos:
            if os.path.exists(tv):
                os.remove(tv)
        if os.path.exists(temp_audio):
            os.remove(temp_audio)

    def generate_stream():
        yield log_event("🎞️ Bat dau ghep nhieu video...")
        yield progress_event(5)

        yield log_event(f"📥 So video: {len(temp_videos)} | Durations nhan duoc: {durations}")
        for i, (path, name, dur) in enumerate(temp_videos):
            size_mb = os.path.getsize(path) / 1024 / 1024
            dur_str = f"cat lay {dur}s" if dur > 0 else "nguyen goc (KHONG cat)"
            yield log_event(f"  Video {i+1}: {name} ({size_mb:.1f} MB) -> {dur_str}")
        yield progress_event(10)

        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(Config.OUTPUT_DIR, f"multi_merged_{unique_id}.mp4")

        temp_processed = []  # Các file tạm sau khi xử lý từng video

        try:
            # Bước 1: Xử lý từng video (cắt/lặp theo duration)
            yield log_event("🔧 Xu ly tung video...")
            yield progress_event(15)

            # Lấy width/height của video đầu tiên làm chuẩn
            probe_size_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                              '-show_entries', 'stream=width,height',
                              '-of', 'csv=s=x:p=0', temp_videos[0][0]]
            probe_size = subprocess.run(probe_size_cmd, capture_output=True, text=True)
            try:
                target_w, target_h = probe_size.stdout.strip().split('x')
                target_w, target_h = int(target_w), int(target_h)
            except:
                target_w, target_h = 1920, 1080

            yield log_event(f"📐 Resolution chuan: {target_w}x{target_h}")

            total_duration = 0
            progress_per_video = 40 / max(len(temp_videos), 1)

            for i, (video_path, video_name, target_dur) in enumerate(temp_videos):
                yield log_event(f"⚙️ Xu ly video {i+1}/{len(temp_videos)}: {video_name}")

                # Lấy duration video gốc
                probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                             '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                orig_dur = float(probe_result.stdout.strip()) if probe_result.returncode == 0 else None

                yield log_event(f"  📹 Video goc: {orig_dur:.1f}s | Yeu cau: {target_dur}s" if orig_dur else f"  📹 Khong doc duoc duration | Yeu cau: {target_dur}s")

                processed_path = os.path.join(Config.TEMP_DIR, f"multi_proc_{unique_id}_{i}.mp4")

                # Scale + ép cùng 30fps (QUAN TRỌNG: tất cả video phải cùng fps để concat không bị lệch timestamp)
                target_fps = 30
                scale_filter = f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},setsar=1:1,fps={target_fps},format=yuv420p"

                # Base ffmpeg args cho mọi trường hợp
                base_output_args = [
                    '-vf', scale_filter,
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                    '-r', str(target_fps),
                    '-video_track_timescale', str(target_fps * 1000),
                    '-an',
                    processed_path
                ]

                if target_dur > 0:
                    if orig_dur and orig_dur >= target_dur:
                        # Video dài hơn yêu cầu -> cắt bớt
                        yield log_event(f"  ✂️ Cat tu {orig_dur:.1f}s xuong {target_dur}s")
                        cmd = ['ffmpeg', '-y', '-i', video_path, '-t', str(target_dur)] + base_output_args
                    elif orig_dur:
                        # Video ngắn hơn yêu cầu -> lặp lại
                        loops = int(target_dur / orig_dur) + 1
                        yield log_event(f"  🔁 Loop {loops} lan ({orig_dur:.1f}s -> {target_dur}s)")
                        cmd = ['ffmpeg', '-y', '-stream_loop', str(loops), '-i', video_path, '-t', str(target_dur)] + base_output_args
                    else:
                        # Không đọc được duration gốc -> vẫn cắt theo target_dur
                        yield log_event(f"  ⚠️ Khong doc duoc duration goc, cat theo {target_dur}s")
                        cmd = ['ffmpeg', '-y', '-i', video_path, '-t', str(target_dur)] + base_output_args
                else:
                    # Không nhập duration -> lấy nguyên gốc
                    yield log_event(f"  ℹ️ Khong nhap duration -> lay nguyen goc {orig_dur:.1f}s" if orig_dur else "  ℹ️ Lay nguyen goc")
                    cmd = ['ffmpeg', '-y', '-i', video_path] + base_output_args
                    target_dur = orig_dur if orig_dur else 10

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    yield log_event(f"⚠️ Loi xu ly video {i+1}: {result.stderr[:200]}", "warn")
                    cleanup_files()
                    for tp in temp_processed:
                        if os.path.exists(tp):
                            os.remove(tp)
                    yield error_event(f"❌ Khong the xu ly video {i+1}")
                    return

                # Probe duration thực sau khi xử lý
                probe_proc_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                  '-of', 'default=noprint_wrappers=1:nokey=1', processed_path]
                probe_proc_result = subprocess.run(probe_proc_cmd, capture_output=True, text=True)
                actual_dur = float(probe_proc_result.stdout.strip()) if probe_proc_result.returncode == 0 else target_dur

                temp_processed.append(processed_path)
                total_duration += actual_dur
                yield log_event(f"  ✓ Video {i+1}: yeu cau {target_dur}s -> thuc te {actual_dur:.2f}s", "success")
                yield progress_event(15 + int(progress_per_video * (i + 1)))

            yield log_event(f"📊 Tong thoi luong (tu tung video): {total_duration:.2f}s")
            yield progress_event(55)

            # Bước 2: Nối các video lại bằng concat filter (đáng tin cậy hơn concat demuxer)
            yield log_event(f"🔗 Dang noi {len(temp_processed)} video lai (concat filter)...")

            concat_path = os.path.join(Config.TEMP_DIR, f"multi_concat_{unique_id}.mp4")

            # Dùng concat filter: xử lý đúng kể cả khi video có profile/level khác nhau
            concat_inputs = []
            filter_parts = []
            for j, pp in enumerate(temp_processed):
                concat_inputs.extend(['-i', pp])
                filter_parts.append(f'[{j}:v]')

            concat_filter = ''.join(filter_parts) + f'concat=n={len(temp_processed)}:v=1:a=0[outv]'

            concat_cmd = ['ffmpeg', '-y'] + concat_inputs + [
                '-filter_complex', concat_filter,
                '-map', '[outv]',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-r', '30',
                '-movflags', '+faststart',
                concat_path
            ]
            result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                yield log_event(f"⚠️ Concat filter that bai, thu concat demuxer...", "warn")
                yield log_event(f"  Loi: {result.stderr[:200]}", "warn")
                # Fallback: concat demuxer
                concat_list = os.path.join(Config.TEMP_DIR, f"multi_concat_list_{unique_id}.txt")
                with open(concat_list, 'w') as f:
                    for pp in temp_processed:
                        f.write(f"file '{os.path.abspath(pp)}'\n")
                concat_cmd = [
                    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                    '-i', concat_list,
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                    concat_path
                ]
                result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=600)
                if os.path.exists(concat_list):
                    os.remove(concat_list)

            if result.returncode != 0:
                yield error_event("❌ Khong the noi video!")
                yield log_event(f"FFmpeg: {result.stderr[:300]}", "error")
                cleanup_files()
                for tp in temp_processed:
                    if os.path.exists(tp):
                        os.remove(tp)
                return

            yield log_event("✓ Da noi video thanh cong", "success")
            yield progress_event(65)

            # Bước 3: Probe duration THỰC của video đã concat (tránh freeze frame cuối)
            probe_concat_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                '-of', 'default=noprint_wrappers=1:nokey=1', concat_path]
            probe_concat_result = subprocess.run(probe_concat_cmd, capture_output=True, text=True)
            actual_video_duration = float(probe_concat_result.stdout.strip()) if probe_concat_result.returncode == 0 else None

            if actual_video_duration:
                yield log_event(f"📏 Thoi luong video thuc te sau concat: {actual_video_duration:.2f}s (yeu cau: {total_duration}s)")
                # Dùng duration thực thay vì duration tính tay để tránh freeze frame cuối
                total_duration = actual_video_duration
            else:
                yield log_event("⚠️ Khong the do thoi luong thuc, dung thoi luong tinh tay", "warn")

            # Bước 4: Ghép audio (loop nếu cần)
            yield log_event("🎵 Dang ghep audio...")

            # Lấy audio duration
            probe_audio_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                               '-of', 'default=noprint_wrappers=1:nokey=1', temp_audio]
            probe_audio_result = subprocess.run(probe_audio_cmd, capture_output=True, text=True)
            audio_duration = float(probe_audio_result.stdout.strip()) if probe_audio_result.returncode == 0 else None

            if audio_duration:
                yield log_event(f"🎵 Audio: {audio_duration:.1f}s | Video: {total_duration:.1f}s")

            # Build video effects filter
            has_effects = len(effects) > 0
            video_filters = []
            audio_filters = []

            if has_effects:
                yield log_event(f"🎨 Ap dung hieu ung: {', '.join(effects)}")

            if 'mirror' in effects:
                video_filters.append('hflip')
            if 'color' in effects:
                video_filters.append('eq=saturation=1.3:contrast=1.1:brightness=0.05')
            if 'zoom' in effects:
                video_filters.append(
                    f"scale={int(target_w*1.1)}:{int(target_h*1.1)},"
                    f"zoompan=z='min(zoom+0.0002,1.1)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={target_w}x{target_h}:fps=30"
                )
            if 'vignette' in effects:
                video_filters.append('vignette=PI/4')
            if 'speed' in effects:
                video_filters.append('setpts=PTS/1.05')
                audio_filters.append('atempo=1.05')

            if 'fade' in effects and total_duration:
                fade_dur = min(2, total_duration * 0.1)
                fade_out_start = total_duration - fade_dur
                video_filters.append(f'fade=t=in:st=0:d={fade_dur:.1f}')
                video_filters.append(f'fade=t=out:st={fade_out_start:.1f}:d={fade_dur:.1f}')
                audio_filters.append(f'afade=t=in:st=0:d={fade_dur:.1f}')
                audio_filters.append(f'afade=t=out:st={fade_out_start:.1f}:d={fade_dur:.1f}')

            vf_str = ','.join(video_filters) if video_filters else None

            # Audio input args (loop nếu cần)
            input_args = ['-i', concat_path]
            if audio_duration and audio_duration < total_duration:
                audio_loop_count = int(total_duration / audio_duration) + 1
                yield log_event(f"🔁 Audio ngan hon -> loop {audio_loop_count} lan")
                input_args.extend(['-stream_loop', str(audio_loop_count), '-i', temp_audio])
            else:
                input_args.extend(['-i', temp_audio])

            # Dùng duration thực (float) để audio khớp chính xác với video
            dur_str = f'{total_duration:.3f}'

            # Audio filter chain
            af_parts = list(audio_filters)
            af_parts.append(f'apad=whole_dur={dur_str}')
            audio_filter_complex = f'[1:a]{",".join(af_parts)}[a]'

            # Build final merge command
            if vf_str:
                full_filter = f'[0:v]{vf_str}[vout];{audio_filter_complex}'
                merge_cmd = ['ffmpeg', '-y'] + input_args + [
                    '-filter_complex', full_filter,
                    '-map', '[vout]', '-map', '[a]',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                    '-c:a', 'aac',
                    '-t', dur_str,
                    output_path
                ]
            else:
                merge_cmd = ['ffmpeg', '-y'] + input_args + [
                    '-filter_complex', audio_filter_complex,
                    '-map', '0:v', '-map', '[a]',
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-t', dur_str,
                    output_path
                ]

            yield progress_event(70)
            yield log_event("⏳ Dang ghep audio vao video...")

            result = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                yield log_event(f"⚠️ Lan 1 that bai, thu re-encode...", "warn")
                # Fallback: bỏ effects phức tạp
                merge_cmd_fallback = ['ffmpeg', '-y'] + input_args + [
                    '-filter_complex', f'[1:a]apad=whole_dur={dur_str}[a]',
                    '-map', '0:v', '-map', '[a]',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                    '-c:a', 'aac',
                    '-t', dur_str,
                    output_path
                ]
                result = subprocess.run(merge_cmd_fallback, capture_output=True, text=True, timeout=600)

                if result.returncode != 0:
                    yield error_event("❌ Khong the ghep audio!")
                    yield log_event(f"FFmpeg: {result.stderr[:500]}", "error")
                    cleanup_files()
                    for tp in temp_processed:
                        if os.path.exists(tp):
                            os.remove(tp)
                    if os.path.exists(concat_path):
                        os.remove(concat_path)
                    return

            yield log_event("✓ Ghep audio thanh cong", "success")
            yield progress_event(90)

            # Kiểm tra output
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                yield error_event("❌ File output loi!")
                cleanup_files()
                for tp in temp_processed:
                    if os.path.exists(tp):
                        os.remove(tp)
                if os.path.exists(concat_path):
                    os.remove(concat_path)
                return

            output_size = os.path.getsize(output_path) / 1024 / 1024
            yield log_event(f"✓ Output: {output_size:.1f} MB", "success")

            # Cleanup
            yield log_event("🗑️ Xoa file tam...")
            cleanup_files()
            for tp in temp_processed:
                if os.path.exists(tp):
                    os.remove(tp)
            if os.path.exists(concat_path):
                os.remove(concat_path)

            yield progress_event(100)
            yield log_event("🎉 HOAN THANH!", "success")
            yield done_event("Ghep nhieu video thanh cong!", [output_path])

        except subprocess.TimeoutExpired:
            yield error_event("⏰ Qua thoi gian xu ly!")
            cleanup_files()
            for tp in temp_processed:
                if os.path.exists(tp):
                    os.remove(tp)
        except Exception as e:
            yield error_event(f"❌ Loi: {str(e)}")
            import traceback
            yield log_event(f"Chi tiet: {traceback.format_exc()[:500]}", "error")
            cleanup_files()
            for tp in temp_processed:
                if os.path.exists(tp):
                    os.remove(tp)

    return Response(generate_stream(), mimetype="text/event-stream")


# ---------- Main ----------

if __name__ == "__main__":
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
    print("\n  AI Video Tool - Web UI")
    print("  http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
