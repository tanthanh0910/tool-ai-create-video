# Huong Dan Chay AI Video Tool

## Yeu Cau He Thong

- macOS (da test tren Apple M1)
- Python 3.12+
- ffmpeg (`brew install ffmpeg`) — bat buoc, dung cho moi khau xu ly video

Khong can Ollama, khong can HuggingFace.

## Cai Dat Lan Dau

```bash
cd /Users/admin/Documents/video
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Cau Hinh

Copy `.env.example` thanh `.env` roi dien:

```env
# BAT BUOC - de tim hinh anh/video thuc
PEXELS_API_KEY=xxxxx        # https://www.pexels.com/api/ (mien phi)

# TUY CHON - cho nut "AI viet gium" tieu de/mo ta/tag
LLM_PROVIDER=anthropic      # anthropic | openai | gemini | aics
LLM_API_KEY=sk-...

# TUY CHON - de dang video len YouTube/Facebook
OAUTH_REDIRECT_BASE=http://localhost:5000
```

**Lay Pexels API Key:** vao https://www.pexels.com/api/ -> Get Started -> dang ky ->
https://www.pexels.com/api/new/ -> copy key dan vao `.env`.

## Chay Tool

```bash
source venv/bin/activate
python app.py
```

Mo trinh duyet: **http://localhost:5000**

Chi can MOT terminal.

## Ba Tab Trong Giao Dien

### 1. 🎬 Video Thuong

Tao video dong vat hoac thuc vat. Chon danh muc, nhap chu de (hoac nhap thang danh
sach cach nhau bang dau phay: `lion, tiger, elephant`), chon ty le khung hinh va so
loai moi video.

- **Dong vat**: doc ten bang giong Viet + tieng keu that (neu co file trong `sounds/`)
- **Thuc vat**: doc ten + nhac nen `sounds/plants/plants.mp3`

Nhap **tieng Anh** cho ket qua tim kiem chinh xac hon.

### 2. 🎞️ Ghep Nhieu Video

Tai len nhieu mp4, moi cai chon thoi luong rieng (ngan hon thi tu lap lai, dai hon
thi cat bot), them 1 file audio, chon hieu ung. Tat ca duoc chuan hoa ve cung
resolution va 30fps truoc khi noi.

### 3. 📡 Kenh Dang Bai

Ket noi YouTube / Facebook roi dang video vua tao. Xem
[docs/youtube-setup.md](docs/youtube-setup.md) va
[docs/facebook-setup.md](docs/facebook-setup.md).

## Short/Reel hay Video Dai?

Khong co tham so API nao khai bao duoc — hai nen tang tu phan loai theo chinh file:

| | Thanh Short / Reel khi |
|---|---|
| YouTube | Khung hinh doc hoac vuong **va** do dai <= 3 phut |
| Facebook | Khung hinh doc |

Nen thu quyet dinh la o **"Ty le khung hinh"** luc tao video, khong phai luc dang.

## Xu Ly Loi Thuong Gap

| Loi | Nguyen nhan | Cach sua |
|-----|-------------|----------|
| `Thieu PEXELS_API_KEY` | Chua dien key | Dien vao `.env` roi chay lai `python app.py` |
| `HTTP 401` (Pexels) | API key sai | Tao key moi tai pexels.com/api |
| `HTTP 429` | Rate limit Pexels (200 req/gio) | Doi 1-2 phut |
| `TTS error: Cannot connect` | Mat mang | Edge TTS can internet |
| `Chua khai LLM_API_KEY` | Chua cau hinh AI viet gium | Dien `LLM_API_KEY` vao `.env` |
| `redirect_uri_mismatch` | Redirect URI ben Google/Meta sai | Copy lai chuoi trong tab Kenh Dang Bai |
| `invalid_grant` (YouTube) | App con o che do Testing | Publish app roi ket noi lai |
| `No module named X` | Chua cai thu vien | `source venv/bin/activate && pip install -r requirements.txt` |
| `ffmpeg: command not found` | Chua cai ffmpeg | `brew install ffmpeg` |

Sua `.env` xong phai **tat han roi chay lai** `python app.py` — bien moi truong chi doc
mot lan luc khoi dong.

## Video Xuat Ra O Dau?

`./output/*.mp4`

Thu muc `./temp/` duoc giu lai co y de debug (xem log tung clip). Xoa tay khi can.
