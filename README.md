# AI Video Tool

Tool tao video tu dong bang AI - chay 100% mien phi tren may tinh ca nhan.

## Tinh nang

- **Tao Video AI**: Nhap chu de -> AI tao kich ban, hinh anh, giong doc -> xuat video MP4
- **Video Dong Vat**: Dung hinh anh/video thuc tu Pexels + giong doc tieng Viet

## Yeu cau he thong

- Python 3.11+
- [Ollama](https://ollama.ai/) (local LLM mien phi)
- [ffmpeg](https://ffmpeg.org/) (xu ly video)

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

# 4. Cai Ollama va tai model
# Tai Ollama tai: https://ollama.ai/
ollama pull llama3.1

# 5. Cai ffmpeg
# Mac:
brew install ffmpeg
# Ubuntu:
# sudo apt install ffmpeg

# 6. Tao file .env
cp .env.example .env
# Sua .env: them HF_TOKEN, PEXELS_API_KEY (deu mien phi)
```

## Lay API keys (mien phi)

| Service | Dang ky | Dung cho |
|---------|---------|----------|
| HuggingFace | https://huggingface.co/settings/tokens | Tao hinh anh AI |
| Pexels | https://www.pexels.com/api/ | Hinh anh/video dong vat thuc |

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
│   ├── script_generator.py     # Tao kich ban (Ollama)
│   ├── image_generator.py      # Tao hinh anh (HuggingFace)
│   ├── audio_generator.py      # Tao giong doc (Edge TTS)
│   ├── video_assembler.py      # Ghep video (ffmpeg)
│   └── animal_video_generator.py  # Video dong vat (Pexels)
├── templates/
│   └── index.html          # Giao dien web
├── .env.example
└── requirements.txt
```

## License

MIT
