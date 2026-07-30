import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Video - kich thuoc thuc do orientation trong UI quyet dinh (16:9 / 9:16 / 1:1)
    FPS = int(os.getenv("FPS", 24))

    # TTS (Edge TTS - mien phi)
    TTS_VOICE = os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural")

    # Pexels API (mien phi, dung cho video/anh thuc te)
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

    # Pixabay API (backup khi Pexels khong co video)
    PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

    # Paths
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
    TEMP_DIR = os.getenv("TEMP_DIR", "./temp")

    # ===== Dang video len YouTube / Facebook =====
    # Bien BAT BUOC duy nhat. Khong co cong, khong co dau / o cuoi.
    # Local: http://localhost:5000 (chinh Flask serve UI nen dung luon cong nay)
    OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:5000").rstrip("/")

    # Khoa ky state JWT + dan xuat khoa ma hoa Fernet cho token.
    # Doi khoa nay = moi token da luu phai ket noi lai.
    JWT_SECRET = os.getenv("JWT_SECRET", "")

    # Noi luu cau hinh kenh (thay cho cot JSONB users.social_channels)
    CHANNELS_FILE = os.getenv("CHANNELS_FILE", "./channels.json")

    # ===== AI viet tieu de / mo ta / tag (video_meta_ai.py) =====
    # anthropic | openai | gemini | aics. De trong model/base_url = dung mac dinh.
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
    # So khung hinh trich cho AI nhin. 4 la du - nhieu hon chi doi token anh.
    LLM_FRAME_COUNT = int(os.getenv("LLM_FRAME_COUNT", 4))

    # App he thong - DUONG LUI khi user chua khai app cua rieng minh.
    # De trong cung chay: user tu khai app trong UI.
    YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
    YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
    FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
    FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
