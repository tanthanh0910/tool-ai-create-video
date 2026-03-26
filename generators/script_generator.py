"""
Script Generator - Dùng Ollama (local LLM miễn phí) để tạo kịch bản video.
Mỗi kịch bản gồm: tiêu đề, lời thoại, và mô tả hình ảnh cho từng cảnh.
"""

import json
import requests
from config import Config


SYSTEM_PROMPT = """Bạn là một biên kịch video chuyên nghiệp, đồng thời là chuyên gia viết prompt cho AI tạo ảnh.

Nhiệm vụ: tạo kịch bản cho nhiều video ngắn. Với mỗi video, bạn cần tạo:
- title: Tiêu đề video (ngắn gọn, hấp dẫn)
- scenes: Danh sách các cảnh, mỗi cảnh gồm:
  - narration: Lời kể/thoại bằng tiếng Việt (2-3 câu, hấp dẫn)
  - image_prompt: Mô tả hình ảnh bằng TIẾNG ANH cho AI tạo ảnh

=== QUY TẮC QUAN TRỌNG CHO image_prompt ===

1. MÔ TẢ NHÂN VẬT CỤ THỂ: Không dùng tên riêng. Thay vào đó mô tả ngoại hình chi tiết.
   SAI: "Sun Wukong fighting monsters"
   ĐÚNG: "A muscular monkey warrior wearing golden armor and a red cape, holding a long golden staff, with fierce golden eyes, standing on clouds, ancient Chinese mythology style"

2. MÔ TẢ BỐI CẢNH CỤ THỂ: Địa điểm, thời gian, ánh sáng, thời tiết.
   SAI: "A temple scene"
   ĐÚNG: "An ancient Chinese Buddhist temple on a misty mountain peak, with red pillars and curved golden roofs, surrounded by clouds at sunset, incense smoke rising"

3. MÔ TẢ PHONG CÁCH: Luôn thêm art style phù hợp với chủ đề.
   - Phim cổ trang Trung Quốc: "Chinese ink painting style, ancient Chinese mythology, wuxia aesthetic"
   - Phim Việt Nam: "Vietnamese traditional art, Southeast Asian landscape"
   - Phim hiện đại: "photorealistic, cinematic lighting, 4k film still"
   - Hoạt hình: "3D Pixar style, vibrant colors, cartoon"

4. CẤU TRÚC image_prompt luôn theo thứ tự:
   [Nhân vật + ngoại hình + hành động], [bối cảnh + chi tiết], [phong cách nghệ thuật + chất lượng]

5. ĐỘ DÀI: Mỗi image_prompt phải 30-60 từ tiếng Anh, càng chi tiết càng tốt.

6. NHẤT QUÁN: Các cảnh trong cùng 1 video phải giữ nhất quán về phong cách và mô tả nhân vật.
   Nếu cảnh 1 mô tả nhân vật mặc áo đỏ, các cảnh sau cũng phải mô tả nhân vật đó giống vậy.

=== FORMAT JSON (CHỈ trả về JSON, không có text khác) ===
{
  "videos": [
    {
      "title": "Tiêu đề video",
      "scenes": [
        {
          "narration": "Lời kể tiếng Việt hấp dẫn...",
          "image_prompt": "A detailed English description following the rules above..."
        }
      ]
    }
  ]
}

Mỗi video nên có 3-4 cảnh. CHỈ trả về JSON thuần, không markdown, không code block.
"""


def generate_scripts(user_prompt: str, num_videos: int = 5) -> list[dict]:
    """Tạo kịch bản cho nhiều video từ prompt của người dùng bằng Ollama."""
    url = f"{Config.OLLAMA_URL}/api/generate"

    user_message = (
        f"Hãy tạo {num_videos} kịch bản video ngắn về chủ đề: {user_prompt}\n\n"
        f"Nhớ: image_prompt phải mô tả ngoại hình nhân vật CỤ THỂ (quần áo, vũ khí, tóc, da, biểu cảm), "
        f"bối cảnh CỤ THỂ (địa điểm, thời tiết, ánh sáng), và phong cách nghệ thuật phù hợp. "
        f"KHÔNG dùng tên riêng trong image_prompt, chỉ mô tả hình ảnh."
    )

    payload = {
        "model": Config.OLLAMA_MODEL,
        "prompt": user_message,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 8000,
        }
    }

    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()

    response_text = response.json()["response"]

    # Parse JSON từ response - xử lý nhiều format
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    # Tìm JSON object trong text - dung bracket matching
    start = response_text.find("{")
    if start == -1:
        raise ValueError("Khong tim thay JSON trong response")

    # Dem bracket de tim dung dau ket thuc JSON
    depth = 0
    end = start
    in_string = False
    escape = False
    for i in range(start, len(response_text)):
        c = response_text[i]
        if escape:
            escape = False
            continue
        if c == '\\' and in_string:
            escape = True
            continue
        if c == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    json_text = response_text[start:end]
    data = json.loads(json_text.strip())
    return data["videos"]
