# AI Video Tool

Tool tao video tu dong bang AI - chay 100% mien phi tren may tinh ca nhan.

## Tinh nang

- **Video Dong Vat / Thuc Vat**: hinh anh + video THUC tu Pexels, doc ten bang giong
  Viet, kem tieng keu that (dong vat) hoac nhac nen (thuc vat)
- **Ghep Nhieu Video**: noi nhieu mp4 + audio + hieu ung, tu chuan hoa resolution/fps
- **Dang len YouTube / Facebook / TikTok**: ket noi kenh roi dang thang video vua tao

## Yeu cau he thong

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) (xu ly video) — bat buoc

## Cai dat

```bash
# 1. Clone repo
git clone https://github.com/YOUR_USERNAME/ai-video-tool.git
cd ai-video-tool

# 2. Tao virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 3. Cai dependencies
pip install -r requirements.txt

# 4. Cai ffmpeg
# Mac:
brew install ffmpeg
# Ubuntu:
# sudo apt install ffmpeg

# 5. Tao file .env
cp .env.example .env
# Sua .env: them PEXELS_API_KEY (mien phi)
```

## Lay API keys

| Service | Dang ky | Dung cho | Bat buoc |
|---------|---------|----------|----------|
| Pexels | https://www.pexels.com/api/ | Hinh anh/video thuc (mien phi) | ✅ |
| LLM | tuy provider | Nut "AI viet gium" tieu de/tag | ❌ |
| YouTube / Facebook / TikTok | xem `docs/` | Dang video len kenh | ❌ |

## Dang video len YouTube / Facebook / TikTok

Moi nguoi tu khai OAuth app cua rieng minh (khong dung app chung), nen dung duoc
ngay ma khong phai cho Google/Meta duyet.

1. Mo tab **📡 Kenh Dang Bai**
2. Bam **⚙ Khai ung dung**, copy **Redirect URI** dan sang Google Cloud / Meta
3. Dan Client ID + Secret vao, **Luu**, roi bam **Ket noi**
4. Tao video xong, bam **📤 Dang Len Kenh** o phan Ket Qua

Huong dan chi tiet: [docs/youtube-setup.md](docs/youtube-setup.md) ·
[docs/facebook-setup.md](docs/facebook-setup.md) ·
[docs/tiktok-setup.md](docs/tiktok-setup.md)

**TikTok co 2 khac biet**: phai khai app dang **Desktop** (Web bat redirect_uri HTTPS nen
localhost khong dung duoc), va video vao **Drafts** chu khong dang thang - vi TikTok ep
moi bai cua app chua qua audit ve private. Ban mo app TikTok bam Dang la ra cong khai.

### Nut "AI viet gium" (tieu de / mo ta / tag)

Dung [video_meta_ai.py](video_meta_ai.py) - module doc lap, **khong dung Ollama**.
Video cua tool khong co phu de nen AI **xem 4 khung hinh trich tu chinh video**
(mocs giua moi khoang, khong lay giay 0 vi dau video thuong la man den / intro).

Khai trong `.env`:

```
LLM_PROVIDER=anthropic      # anthropic | openai | gemini | aics
LLM_API_KEY=sk-...
LLM_MODEL=                  # de trong = mac dinh cua provider
```

O "Tu khoa dinh huong" chi de goi y - neu khong khop noi dung thuc trong khung hinh
thi AI bo qua chu khong bia ra noi dung cho vua tu khoa.

`tags` la tu khoa **tim kiem** (nguoi xem khong thay). `hashtags` hien trong mo ta -
tool suy ra tu cac tag ngan. Hai thu khac nhau.

Token luu trong `channels.json`, ma hoa Fernet bang khoa dan xuat tu `JWT_SECRET`.
Doi `JWT_SECRET` = moi kenh phai ket noi lai. Ca hai file deu da duoc gitignore.

## Chay

```bash
source venv/bin/activate
python app.py
```

Mo trinh duyet: http://localhost:5000

## Cau truc

```
├── app.py                  # Flask web server
├── config.py               # Cau hinh
├── generators/
│   ├── animal_video_generator.py  # Video dong vat (Pexels + TTS + tieng keu)
│   └── plant_video_generator.py   # Video thuc vat (Pexels + TTS + nhac nen)
├── video_meta_ai.py        # AI viet title/description/tags (doc lap, da provider)
├── social/                 # Dang video len YouTube / Facebook
│   ├── store.py                # Luu cau hinh kenh (Fernet)
│   ├── oauth.py                # State, authorize_url, doi code lay token
│   ├── verify.py               # Goi that API roi ghi verified_at
│   ├── publish.py              # Upload YouTube resumable + Facebook Graph
│   └── routes.py               # Blueprint 7 endpoint + /api/publish
├── templates/
│   └── index.html          # Giao dien web
├── docs/                   # Huong dan lay khoa YouTube / Facebook
├── .env.example
└── requirements.txt
```

## License

MIT
