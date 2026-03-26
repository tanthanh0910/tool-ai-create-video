import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Video - 16:9 landscape (YouTube style) thay vì 9:16 portrait (TikTok)
    VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", 1920))   # Full HD ngang
    VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", 1080)) # Full HD ngang
    FPS = int(os.getenv("FPS", 24))
    SECONDS_PER_IMAGE = int(os.getenv("SECONDS_PER_IMAGE", 5))

    # TTS (Edge TTS - mien phi)
    TTS_VOICE = os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural")
    TTS_RATE = os.getenv("TTS_RATE", "+0%")

    # Ollama (local LLM - mien phi)
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

    # Hugging Face (free account, khong mat tien)
    HF_TOKEN = os.getenv("HF_TOKEN", "")
    HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")

    # Pexels API (mien phi, dung cho video/anh thuc te)
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
    
    # Pixabay API (backup, mien phi)
    PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

    # Paths
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
    TEMP_DIR = os.getenv("TEMP_DIR", "./temp")
    MAX_PARALLEL_VIDEOS = int(os.getenv("MAX_PARALLEL_VIDEOS", 3))
