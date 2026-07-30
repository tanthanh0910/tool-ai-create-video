# Flow Hoat Dong Cua AI Video Tool

## Tong Quan

Ba chuc nang, tat ca dieu khien tu web UI (`http://localhost:5000`):

1. **Tao video dong vat / thuc vat** — hinh anh + video THUC tu Pexels
2. **Ghep nhieu video** — noi nhieu mp4 + audio + hieu ung
3. **Dang len YouTube / Facebook** — OAuth roi upload

## Cau Truc Thu Muc

```
video/
├── app.py                          # Web UI server (Flask) - http://localhost:5000
├── config.py                       # Doc cau hinh tu .env
├── video_meta_ai.py                # AI viet title/description/tags (module doc lap)
├── generators/
│   ├── animal_video_generator.py   # Video dong vat: Pexels + TTS + tieng keu
│   └── plant_video_generator.py    # Video thuc vat: Pexels + TTS + nhac nen
├── social/                         # Dang bai
│   ├── store.py                    # Luu cau hinh kenh (Fernet)
│   ├── oauth.py                    # State, authorize_url, doi code lay token
│   ├── verify.py                   # Goi that API roi ghi verified_at
│   ├── publish.py                  # YouTube resumable + Facebook Graph
│   └── routes.py                   # Blueprint 7 endpoint + /api/publish
├── templates/index.html            # Giao dien Web UI (3 tab)
├── docs/                           # Huong dan lay khoa YouTube / Facebook
├── sounds/                         # Tieng keu dong vat (~300 file)
├── assets/intro_clip.mp4           # Clip mo dau chen vao dau moi video
├── output/                         # Video xuat ra
└── temp/                           # File tam (GIU LAI de debug)
```

## Flow 1: Tao Video Dong Vat / Thuc Vat

```
Nguoi dung nhap chu de (hoac danh sach: "lion, tiger, elephant")
         |
         v
   Co dau phay va moi phan ngan? ---Yes---> dung thang danh sach do
         | No
         v
   generate_animal_scripts() / generate_plant_scripts()
   - Random tu DATABASE (~300 loai dong vat / ~250 loai thuc vat)
   - Loc theo chu de neu prompt khop keyword (bien, chim, con trung, ...)
         |
         v
   Voi TUNG loai, create_animal_clip() / create_plant_clip():
   +--------------------------------------------------+
   | 1. Tao audio TRUOC (de biet do dai clip)         |
   |    - Edge TTS doc ten tieng Viet                 |
   |    - Ghep them tieng keu tu sounds/<ten>.mp3     |
   |      (dong vat), hoac de trong (thuc vat)        |
   |    - Them 0.5s im lang truoc + 4s sau            |
   +--------------------------------------------------+
   | 2. Tim media tu Pexels                           |
   |    - Search VIDEO truoc, dung orientation dung   |
   |    - Thu nhieu query: chinh xac -> tong quat     |
   |    - Validate: bo video co nguoi / loai khac     |
   |    - Khong co video -> Pixabay -> anh tinh       |
   +--------------------------------------------------+
   | 3. Resize + crop giua, loop neu video ngan hon   |
   |    audio; ghep audio vao (mix tieng keu goc neu  |
   |    video co san am thanh > -35dB)                |
   +--------------------------------------------------+
         |
         v
   concatenate_videos(): [intro] + clip_1 + clip_2 + ...
   - Chuan hoa tung clip sang MPEG-TS
   - Noi bang concat: protocol (khong tich luy encoder delay)
   - Thuc vat: them buoc add_background_music()
         |
         v
   output/01_TenVideo.mp4
```

## Flow 2: Ghep Nhieu Video

```
Upload nhieu mp4 + 1 audio + chon hieu ung
         |
         v
Lay resolution cua video DAU TIEN lam chuan
         |
         v
Voi tung video: scale + crop + ep 30fps
  - duration da nhap > do dai goc  -> -stream_loop
  - duration da nhap < do dai goc  -> cat bot
  - khong nhap                     -> giu nguyen goc
  (Ep cung fps la bat buoc, khong thi concat bi lech timestamp)
         |
         v
Noi bang concat filter (fallback: concat demuxer)
         |
         v
Do lai do dai THUC sau concat (tranh freeze frame cuoi)
         |
         v
Ghep audio: loop neu ngan hon video, apad cho khop
Ap hieu ung: mirror / color / zoom / vignette / speed / fade
         |
         v
output/multi_merged_xxx.mp4
```

## Flow 3: Dang Len YouTube / Facebook

```
Tab "Kenh Dang Bai" -> Khai ung dung (Client ID + Secret cua CHINH user)
         |
         v
Bam Ket noi
  -> GET  /api/me/channels/{provider}/connect    tra { url }
  -> Trinh duyet sang Google / Meta, user cap quyen
  -> GET  /api/me/channels/{provider}/callback?code=&state=
     - state la token ky, han 10 phut, kiem ca provider khop
     - doi code lay token
     - kiem ket noi lai co trung dung kenh cu khong
     - verify ngay bang cach goi that API
  -> redirect ve /?tab=channels&status=&msg=
         |
         v
Chon video trong output/ -> chon kenh -> (tuy chon) bam "AI viet gium"
         |                                       |
         |                                       v
         |                        video_meta_ai: trich 4 khung hinh
         |                        -> LLM tra title/description/tags
         v
POST /api/publish (SSE)
  - YouTube: refresh_token -> access_token -> resumable upload theo khoi 8MB
  - Facebook: POST /{page_id}/videos, caption = title + description + hashtag
  - Mot kenh loi KHONG keo kenh con lai theo; file van con trong output/
```

## Cong Nghe Su Dung

| Thanh phan | Cong nghe | Chi phi |
|------------|-----------|---------|
| Hinh anh / video thuc | Pexels API (backup: Pixabay) | Mien phi |
| Giong doc tieng Viet | Microsoft Edge TTS | Mien phi |
| Tieng keu dong vat | File local trong `sounds/` | Mien phi |
| Xu ly video | ffmpeg | Mien phi |
| AI viet title/tag | anthropic / openai / gemini / aics | Tra tien theo provider |
| Dang bai | YouTube Data API v3, Facebook Graph API | Mien phi |
| Web UI | Flask + vanilla JS + SSE | Mien phi |

## Luu Y Quan Trong

1. **ffmpeg phai cai san** — `brew install ffmpeg`
2. **PEXELS_API_KEY bat buoc** — 200 request/gio o goi mien phi
3. **Edge TTS can internet**
4. **Nhap ten tieng Anh** cho ket qua Pexels chinh xac hon
5. **Thu muc `temp/` KHONG bi xoa** — co y, de doc log tung clip khi debug
6. **Short/Reel do ty le khung hinh + do dai quyet dinh**, khong phai do tham so khi dang
