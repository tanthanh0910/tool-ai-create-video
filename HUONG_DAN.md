# Huong Dan Chay AI Video Tool

## Yeu Cau He Thong

- macOS (da test tren Apple M1)
- Python 3.12+
- ffmpeg (`brew install ffmpeg`)
- Ollama (`brew install ollama`)

## Cai Dat Lan Dau

### Buoc 1: Clone va vao thu muc

```bash
cd /Users/admin/Documents/video
```

### Buoc 2: Tao virtual environment va cai thu vien

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install yt-dlp    # (tuy chon) de tai video tu YouTube/TikTok
```

### Buoc 3: Tai model AI cho Ollama

```bash
ollama pull llama3.1
```

### Buoc 4: Cau hinh API key

Sua file `.env`:

```env
# Bat buoc cho che do AI Art:
HF_TOKEN=hf_xxxxx    # Lay tai https://huggingface.co/settings/tokens (mien phi)

# Bat buoc cho che do Video Dong Vat (hinh/video thuc):
PEXELS_API_KEY=xxxxx # Lay tai https://www.pexels.com/api/ (mien phi)
```

**Cach lay Pexels API Key:**
1. Vao https://www.pexels.com/api/
2. Click "Get Started" -> Dang ky tai khoan (mien phi)
3. Vao https://www.pexels.com/api/new/ de tao API key
4. Copy key va dan vao file `.env`

Cac thong so khac co the giu mac dinh.

## Chay Tool

### Cach 1: Web UI (khuyen dung)

Mo **2 terminal**:

**Terminal 1** - chay Ollama:
```bash
ollama serve
```

**Terminal 2** - chay Web UI:
```bash
cd /Users/admin/Documents/video
source venv/bin/activate
python app.py
```

Mo trinh duyet: **http://localhost:5000**

### 2 Che Do Tao Video:

1. **🎨 AI Art (HuggingFace)**: Tao hinh anh bang AI
   - Phu hop: video truyen thuyet, phim, sang tao
   - Can: HF_TOKEN
   
2. **📷 Hinh/Video Thuc (Pexels)**: Tim hinh anh/video thuc tu Internet
   - Phu hop: video dong vat, thien nhien, giao duc
   - Can: PEXELS_API_KEY
   - Co am thanh doc ten dong vat

### Cach 2: Command line

```bash
source venv/bin/activate

# Tao video AI
python main.py generate "chu de video" -n 3

# Cat video tu file local
python main.py split /duong/dan/video.mp4 -n 5

# Cat video tu URL YouTube/TikTok
python main.py split "https://youtube.com/watch?v=xxx" -s 60

# Che do interactive (menu lua chon)
python main.py
```

## Cau Truc File .env

```env
# Kich thuoc video (mac dinh: dung 9:16 cho short)
VIDEO_WIDTH=1080
VIDEO_HEIGHT=1920
FPS=24
SECONDS_PER_IMAGE=5

# Giong doc tieng Viet
TTS_VOICE=vi-VN-HoaiMyNeural       # Nu
# TTS_VOICE=vi-VN-NamMinhNeural    # Nam
TTS_RATE=+0%                        # Tang/giam toc do: +10%, -10%

# Ollama
OLLAMA_MODEL=llama3.1
OLLAMA_URL=http://localhost:11434

# Hugging Face (mien phi) - cho che do AI Art
HF_TOKEN=hf_xxxxx
HF_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell

# Pexels API (mien phi) - cho che do Video Dong Vat
PEXELS_API_KEY=xxxxx

# Thu muc xuat
OUTPUT_DIR=./output
TEMP_DIR=./temp
MAX_PARALLEL_VIDEOS=3
```

## Xu Ly Loi Thuong Gap

| Loi | Nguyen nhan | Cach sua |
|-----|-------------|----------|
| `Connection refused :11434` | Ollama chua chay | Chay `ollama serve` o terminal khac |
| `HTTP 401` (HuggingFace) | Token sai/het han | Tao token moi tai huggingface.co/settings/tokens |
| `HTTP 401` (Pexels) | API key sai | Tao key moi tai pexels.com/api |
| `HTTP 429` | Rate limit | Doi 1-2 phut roi chay lai |
| `HTTP 503` | Model dang load | Tu dong retry, doi 20-30s |
| `TTS error: Cannot connect` | Mat mang | Kiem tra ket noi internet |
| `yt-dlp error` | URL sai hoac video private | Kiem tra URL, dam bao video public |
| `No module named X` | Chua cai thu vien | `source venv/bin/activate && pip install -r requirements.txt` |

## Video Xuat Ra O Dau?

- Video AI tao: `./output/*.mp4`
- Video da cat: `./output/splits/*.mp4`
