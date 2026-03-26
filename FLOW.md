# Flow Hoat Dong Cua AI Video Tool

## Tong Quan

Tool nay co 2 chuc nang chinh:
1. **Tao video AI**: Nhap chu de -> AI tao kich ban + hinh anh + giong doc -> ghep thanh video
2. **Cat video**: Nhap URL hoac file local -> tai ve -> cat thanh nhieu doan ngan

## Cau Truc Thu Muc

```
video/
├── app.py                          # Web UI server (Flask) - chay http://localhost:5000
├── main.py                         # CLI entry point (chay bang command line)
├── pipeline.py                     # Dieu phoi toan bo quy trinh tao video AI
├── config.py                       # Doc cau hinh tu file .env
├── .env                            # Cau hinh (API key, thong so video)
├── requirements.txt                # Thu vien Python can cai
├── generators/
│   ├── script_generator.py         # Tao kich ban bang Ollama (local LLM)
│   ├── image_generator.py          # Tao hinh anh bang HuggingFace API
│   ├── audio_generator.py          # Tao giong doc bang Edge TTS
│   ├── video_assembler.py          # Ghep anh + audio thanh video (MoviePy)
│   └── video_splitter.py           # Tai + cat video tu URL/file (ffmpeg + yt-dlp)
├── templates/
│   └── index.html                  # Giao dien Web UI
├── output/                         # Thu muc chua video xuat ra
│   └── splits/                     # Thu muc chua video da cat
├── temp/                           # Thu muc tam (tu dong xoa sau khi xong)
└── venv/                           # Python virtual environment
```

## Flow 1: Tao Video AI

```
Nguoi dung nhap chu de (VD: "phim tay du ky")
         |
         v
+---------------------+
| script_generator.py |  Buoc 1: Tao kich ban
|                     |
| - Gui prompt toi Ollama (llama3.1 chay local)
| - Ollama tra ve JSON gom nhieu video
| - Moi video co: title + scenes[]
| - Moi scene co:
|     narration: loi ke tieng Viet
|     image_prompt: mo ta hinh anh tieng Anh (chi tiet)
+---------------------+
         |
         v
+---------------------+     +---------------------+
| image_generator.py  |     | audio_generator.py  |  Buoc 2: Chay SONG SONG
|                     |     |                     |
| - Gui image_prompt  |     | - Gui narration     |
|   toi HuggingFace   |     |   toi Edge TTS      |
|   (FLUX.1-schnell)  |     |   (Microsoft)       |
| - Nhan ve file .png |     | - Nhan ve file .mp3 |
| - 1 anh/scene       |     | - 1 audio/scene     |
+---------------------+     +---------------------+
         |                           |
         +--------+    +-------------+
                  |    |
                  v    v
         +---------------------+
         | video_assembler.py  |  Buoc 3: Ghep video
         |                     |
         | - Doc tung cap (anh + audio)
         | - Tao ImageClip voi duration = do dai audio
         | - Resize ve 1080x1920 (dung 9:16)
         | - Them hieu ung fade in/out
         | - Noi tat ca clip lai (concatenate)
         | - Xuat ra file .mp4 (codec H.264 + AAC)
         +---------------------+
                  |
                  v
         output/01_TenVideo.mp4
         output/02_TenVideo.mp4
         ...
```

### Chi Tiet Tung Module

**script_generator.py**
- Ket noi: Ollama API tai `http://localhost:11434/api/generate`
- Model: llama3.1 (chay local, mien phi)
- Prompt duoc thiet ke de:
  + Khong dung ten rieng trong image_prompt (AI tao anh khong biet ten)
  + Mo ta ngoai hinh nhan vat cu the (quan ao, vu khi, toc, bieu cam)
  + Mo ta boi canh cu the (dia diem, thoi tiet, anh sang)
  + Giu nhat quan phong cach giua cac canh
- Output: JSON `{"videos": [{"title": "...", "scenes": [...]}]}`

**image_generator.py**
- Ket noi: HuggingFace Router API tai `router.huggingface.co`
- Model: FLUX.1-schnell (nhanh, chat luong tot, mien phi)
- Can HF_TOKEN (tao mien phi tai huggingface.co)
- Xu ly tuan tu (1 anh/lan) de tranh rate limit
- Co retry 3 lan + xu ly 503 (model loading) va 429 (rate limit)

**audio_generator.py**
- Ket noi: Microsoft Edge TTS (mien phi, khong can API key)
- Giong mac dinh: `vi-VN-HoaiMyNeural` (giong nu tieng Viet)
- Tao SONG SONG tat ca audio cung luc (nhe, nhanh)

**video_assembler.py**
- Dung MoviePy v2 de ghep video
- Moi scene = 1 ImageClip + 1 AudioFileClip
- Duration clip = max(do dai audio, SECONDS_PER_IMAGE)
- Codec: H.264 video + AAC audio
- Preset: ultrafast (uu tien toc do)

## Flow 2: Cat Video

```
Nguoi dung nhap URL hoac chon file
         |
         v
   URL? ----Yes----> download_video()
    |                    |
    No                   | Dung yt-dlp de tai
    |                    | (ho tro YouTube, TikTok, Facebook, ...)
    v                    v
  File local        File da tai
         |              |
         +------+-------+
                |
                v
     get_video_duration()     Buoc 1: Doc thong tin
     (dung ffprobe)
                |
                v
     Cat theo lua chon:       Buoc 2: Cat video
     +---------------------------+
     | Cach 1: split_by_count()  |  Cat thanh N phan bang nhau
     | Cach 2: split_by_duration | Cat moi X giay
     +---------------------------+
     Dung ffmpeg voi `-c copy` (khong re-encode -> cuc nhanh)
                |
                v
     output/splits/part_001.mp4
     output/splits/part_002.mp4
     ...
```

## Flow Web UI (app.py)

```
Trinh duyet (http://localhost:5000)
         |
         | HTML/CSS/JS (templates/index.html)
         |
         v
+------------------+
| Flask Web Server |
|                  |
| GET  /                    -> Tra ve trang index.html
| POST /api/generate        -> Tao video AI (SSE stream)
| POST /api/split           -> Cat video tu URL (SSE stream)
| POST /api/split-file      -> Cat video tu file upload (SSE stream)
| GET  /download/<filepath> -> Tai file ket qua
+------------------+
         |
         | Server-Sent Events (SSE)
         | -> Log realtime
         | -> Progress bar
         | -> Ket qua + link tai
         |
         v
    Nguoi dung thao tac tren giao dien
```

## Cong Nghe Su Dung

| Thanh phan | Cong nghe | Chi phi |
|------------|-----------|---------|
| Tao kich ban | Ollama + llama3.1 (chay local) | Mien phi |
| Tao hinh anh | HuggingFace + FLUX.1-schnell | Mien phi (can account) |
| Tao giong doc | Microsoft Edge TTS | Mien phi |
| Ghep video | MoviePy + ffmpeg | Mien phi |
| Tai video | yt-dlp | Mien phi |
| Cat video | ffmpeg | Mien phi |
| Web UI | Flask + vanilla JS | Mien phi |

## Luu Y Quan Trong

1. **Ollama phai chay truoc** (`ollama serve`) khi tao video AI
2. **HuggingFace co rate limit** - mien phi khoang 30 request/gio
3. **Edge TTS can internet** - de ket noi Microsoft servers
4. **ffmpeg can cai san** - `brew install ffmpeg`
5. **Video 9:16** (dung) mac dinh - phu hop TikTok/YouTube Shorts/Reels
