"""AI viết tiêu đề / mô tả / tag cho video, từ phụ đề và/hoặc khung hình.

Module ĐỘC LẬP — copy đúng một file này sang dự án khác là chạy. Không import gì của
Rổ Voice, không đọc biến môi trường của ai, không cần database.

    pip install httpx          # bắt buộc
    ffmpeg trong PATH          # chỉ cần nếu muốn cho AI NHÌN video

Dùng nhanh:

    from video_meta_ai import LLMConfig, suggest

    cfg = LLMConfig(provider="anthropic", api_key="sk-ant-...")
    meta = await suggest(cfg, subtitle_text=phu_de)
    # {"title": "...", "description": "...", "tags": ["...", ...]}

Không có phụ đề thì đưa đường dẫn video, hàm tự trích khung hình cho model nhìn:

    meta = await suggest(cfg, video_path="video.mp4")

Bốn nhà cung cấp: anthropic / openai / gemini / aics (cổng nội bộ). Cả bốn đều được ép
trả JSON đúng schema, nên KHÔNG phải bóc kết quả bằng regex.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import subprocess
from dataclasses import dataclass, field

import httpx

log = logging.getLogger("video_meta_ai")

__all__ = ["LLMConfig", "MetaError", "suggest", "suggest_sync", "extract_frames",
           "probe_duration_ms", "build_prompt", "sanitize"]


class MetaError(RuntimeError):
    """Lỗi đã dịch sang câu đọc được, ném thẳng ra cho người dùng cuối xem."""


# ── Cấu hình nhà cung cấp ───────────────────────────────────────────────────

_DEFAULT_BASE = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com",
    "gemini": "https://generativelanguage.googleapis.com",
    "aics": "https://aics.freeapps.vn",
}
_DEFAULT_MODEL = {
    "anthropic": "claude-sonnet-5",
    "openai": "gpt-4o",
    "gemini": "gemini-2.5-flash",
    "aics": "",          # cổng tự chốt model phía máy chủ
}


@dataclass
class LLMConfig:
    provider: str = "anthropic"        # anthropic | openai | gemini | aics
    api_key: str = ""
    model: str = ""                    # trống → mặc định của provider
    base_url: str = ""                 # trống → mặc định; đổi để trỏ qua proxy riêng
    max_tokens: int = 2048
    timeout: float = 120.0

    def __post_init__(self):
        self.provider = (self.provider or "anthropic").lower()
        if self.provider not in _DEFAULT_BASE:
            raise MetaError(f"Provider không hỗ trợ: {self.provider}")
        self.base_url = (self.base_url or _DEFAULT_BASE[self.provider]).rstrip("/")
        self.model = self.model or _DEFAULT_MODEL[self.provider]


# ── Giới hạn của nền tảng ───────────────────────────────────────────────────

MAX_SOURCE = 6000     # ký tự phụ đề đưa vào prompt
MAX_TITLE = 100       # giới hạn CỨNG của YouTube
MAX_DESC = 5000
MAX_TAGS = 15


@dataclass
class Rules:
    """Chỉnh khi dùng cho ngôn ngữ / nền tảng khác."""
    language: str = "tiếng Việt"
    n_tags: str = "8-15"
    desc_shape: str = "2-4 đoạn ngắn"
    extra: list[str] = field(default_factory=list)   # thêm luật riêng của bạn


_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": f"Tiêu đề, tối đa {MAX_TITLE} ký tự"},
        "description": {"type": "string", "description": "Mô tả, vài đoạn ngắn"},
        "tags": {"type": "array", "items": {"type": "string"},
                 "description": "Từ khoá, KHÔNG kèm dấu #"},
    },
    "required": ["title", "description", "tags"],
    "additionalProperties": False,
}


def _system(r: Rules) -> str:
    lines = [
        "Bạn là chuyên gia tối ưu nội dung video cho YouTube và Facebook.",
        "",
        "Nhiệm vụ: xem tư liệu của một video (phụ đề và/hoặc vài khung hình trích ra từ",
        "video) rồi viết tiêu đề, mô tả và tag để đăng.",
        "",
        "QUY TẮC:",
        f'- "title": {r.language}, tối đa {MAX_TITLE} ký tự, hấp dẫn nhưng KHÔNG giật gân sai sự thật.',
        f'- "description": {r.language}, {r.desc_shape}, tóm tắt nội dung thật của video.',
        f'- "tags": {r.n_tags} từ khoá {r.language} (xen tiếng Anh được nếu là thuật ngữ phổ',
        "  biến), KHÔNG kèm dấu #, mỗi tag 1-4 từ.",
        "- Chỉ mô tả những gì THỰC SỰ thấy trong tư liệu. Không bịa thông tin, số liệu, tên",
        "  người, địa danh, hay lời thoại không có.",
        "- Khi chỉ có khung hình: mô tả đúng thứ nhìn thấy, đừng suy diễn cốt truyện hay lời nói.",
    ]
    lines += [f"- {x}" for x in r.extra]
    return "\n".join(lines)


def build_prompt(subtitle_text: str = "", keywords: str = "", n_frames: int = 0) -> str:
    parts: list[str] = []
    src = (subtitle_text or "").strip()[:MAX_SOURCE]
    if src:
        parts.append(f"Phụ đề / lời thoại của video:\n---\n{src}\n---")
    if n_frames:
        # Nói rõ ảnh là KHUNG RỜI theo thời gian, nếu không model dễ kể thành một câu
        # chuyện liên tục giữa các khung.
        parts.append(
            f"Kèm theo {n_frames} khung hình trích rải đều theo thời lượng video "
            "(ảnh rời tại các mốc khác nhau, không phải chuỗi liên tục)."
        )
    if src and n_frames:
        parts.append("Ưu tiên phụ đề khi nói về nội dung; dùng khung hình để nắm bối cảnh hình ảnh.")
    if (keywords or "").strip():
        # Từ khoá ĐỊNH HƯỚNG, không được thay thế nội dung thật — nói rõ để model không bịa
        # ra một video khác chỉ vì người dùng gõ vài từ khoá.
        parts.append(
            f"Từ khoá người dùng muốn nhắm tới: {keywords.strip()[:300]}\n"
            "Hãy ưu tiên đưa các từ khoá này vào tiêu đề/mô tả/tag NẾU chúng thật sự khớp "
            "với nội dung video. Nếu không khớp thì bỏ qua, đừng bịa nội dung cho vừa từ khoá."
        )
    if not parts:
        raise MetaError("Không có tư liệu nào để AI đọc (thiếu cả phụ đề lẫn khung hình)")
    return "\n\n".join(parts)


def sanitize(data: dict) -> dict:
    """Ép đầu ra của model vào giới hạn thật của nền tảng.

    Schema chỉ bảo đảm KIỂU dữ liệu — không bảo đảm tiêu đề dưới 100 ký tự hay tag sạch dấu #.
    """
    title = str(data.get("title") or "").strip()[:MAX_TITLE]
    description = str(data.get("description") or "").strip()[:MAX_DESC]

    tags: list[str] = []
    seen: set[str] = set()
    for t in data.get("tags") or []:
        t = str(t).strip().lstrip("#").strip()[:60]
        if t and t.lower() not in seen:
            seen.add(t.lower())
            tags.append(t)
        if len(tags) >= MAX_TAGS:
            break

    if not title and not description:
        raise MetaError("AI không trả về nội dung dùng được")
    return {"title": title, "description": description, "tags": tags}


# ── Khung hình ──────────────────────────────────────────────────────────────

FRAME_COUNT = 4       # đủ nắm bối cảnh mà không đội token ảnh
FRAME_WIDTH = 768     # ngưỡng model vẫn nhìn rõ chi tiết
_FFMPEG_TIMEOUT = 20


def probe_duration_ms(video_path: str) -> int:
    """Thời lượng video, mili giây. Không đọc được → 0."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", video_path],
            capture_output=True, timeout=_FFMPEG_TIMEOUT, text=True,
        )
        return int(float(r.stdout.strip()) * 1000) if r.returncode == 0 else 0
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return 0


def extract_frames(video_path: str, duration_ms: int = 0,
                   count: int = FRAME_COUNT) -> list[bytes]:
    """Trả list ảnh JPEG lấy rải đều theo thời lượng. Lỗi → list rỗng (không ném).

    Mốc lấy ở GIỮA mỗi khoảng chia đều, không lấy giây 0 — khung đầu video hay là màn đen,
    logo hoặc fade-in, không đại diện cho nội dung.

    `-ss` đặt TRƯỚC `-i` để ffmpeg nhảy thẳng tới mốc thay vì giải mã từ đầu; video dài vẫn nhanh.
    """
    duration_ms = duration_ms or probe_duration_ms(video_path)
    if duration_ms <= 0:
        return []
    out: list[bytes] = []
    for i in range(count):
        ts = duration_ms * (i + 0.5) / count / 1000.0
        try:
            r = subprocess.run(
                ["ffmpeg", "-nostdin", "-ss", f"{ts:.3f}", "-i", video_path,
                 "-frames:v", "1", "-vf", f"scale={FRAME_WIDTH}:-2", "-q:v", "4",
                 "-f", "image2", "-c:v", "mjpeg", "-"],
                capture_output=True, timeout=_FFMPEG_TIMEOUT,
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            log.warning("trích khung %d/%d lỗi: %s", i + 1, count, e)
            continue
        if r.returncode == 0 and r.stdout:
            out.append(r.stdout)
        else:
            log.warning("ffmpeg không trích được khung tại %.2fs", ts)
    return out


# ── Gọi LLM ─────────────────────────────────────────────────────────────────

def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _mime_of(b: bytes) -> str:
    return "image/png" if b[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"


def _to_gemini_schema(schema: dict) -> dict:
    """JSON Schema chuẩn → tập con OpenAPI của Gemini: kiểu VIẾT HOA, bỏ
    additionalProperties (Gemini từ chối khoá này)."""
    out: dict = {}
    for k, v in schema.items():
        if k == "additionalProperties":
            continue
        if k == "type" and isinstance(v, str):
            out[k] = v.upper()
        elif k == "properties" and isinstance(v, dict):
            out[k] = {pk: _to_gemini_schema(pv) for pk, pv in v.items()}
        elif k == "items" and isinstance(v, dict):
            out[k] = _to_gemini_schema(v)
        else:
            out[k] = v
    return out


def _build(cfg: LLMConfig, system: str, user: str, images: list[bytes]) -> tuple[str, dict, dict]:
    if cfg.provider == "aics":
        # Cổng nội bộ không có trường `system` → gộp vào prompt, ngăn bằng một dòng rõ ràng
        # để model vẫn phân biệt phần "luật" với phần "việc".
        body: dict = {"prompt": f"{system}\n\n---\n\n{user}", "allowWebSearch": False,
                      "jsonSchema": _SCHEMA}
        if images:
            body["images"] = [{"base64": _b64(i), "mime": _mime_of(i)} for i in images]
        return (f"{cfg.base_url}/v1/ai/chat",
                {"x-api-key": cfg.api_key, "content-type": "application/json"}, body)

    if cfg.provider == "gemini":
        parts: list[dict] = [{"inline_data": {"mime_type": _mime_of(i), "data": _b64(i)}}
                             for i in images]
        parts.append({"text": user})
        return (
            f"{cfg.base_url}/v1beta/models/{cfg.model}:generateContent?key={cfg.api_key}",
            {"content-type": "application/json"},
            {"system_instruction": {"parts": [{"text": system}]},
             "contents": [{"role": "user", "parts": parts}],
             "generationConfig": {"temperature": 0.2, "maxOutputTokens": cfg.max_tokens,
                                  "responseMimeType": "application/json",
                                  "responseSchema": _to_gemini_schema(_SCHEMA)}},
        )

    if cfg.provider == "openai":
        content: list[dict] = [
            {"type": "image_url", "image_url": {"url": f"data:{_mime_of(i)};base64,{_b64(i)}"}}
            for i in images
        ]
        content.append({"type": "text", "text": user})
        return (f"{cfg.base_url}/v1/chat/completions",
                {"Authorization": f"Bearer {cfg.api_key}", "content-type": "application/json"},
                {"model": cfg.model, "max_tokens": cfg.max_tokens,
                 "messages": [{"role": "system", "content": system},
                              {"role": "user", "content": content}],
                 "response_format": {"type": "json_schema", "json_schema": {
                     "name": "result", "strict": True, "schema": _SCHEMA}}})

    # anthropic
    blocks: list[dict] = [
        {"type": "image", "source": {"type": "base64", "media_type": _mime_of(i), "data": _b64(i)}}
        for i in images
    ]
    blocks.append({"type": "text", "text": user})
    return (f"{cfg.base_url}/v1/messages",
            {"x-api-key": cfg.api_key, "anthropic-version": "2023-06-01",
             "content-type": "application/json"},
            {"model": cfg.model, "max_tokens": cfg.max_tokens, "system": system,
             "messages": [{"role": "user", "content": blocks}],
             # API BẢO ĐẢM khối text đầu tiên là JSON đúng schema — khỏi bóc bằng regex.
             "output_config": {"format": {"type": "json_schema", "schema": _SCHEMA}}})


def _extract(cfg: LLMConfig, data: dict):
    """Bóc phần trả lời. Trả chuỗi, HOẶC dict nếu cổng đã tự parse sẵn (aics)."""
    if cfg.provider == "aics":
        r = data.get("result")
        if isinstance(r, dict) and "text" not in r:
            return r
        return (r or {}).get("text", "") if isinstance(r, dict) else str(r or "")
    if cfg.provider == "gemini":
        cands = data.get("candidates") or []
        if not cands:
            raise MetaError("AI không trả về kết quả nào")
        return "".join(p.get("text", "")
                       for p in cands[0].get("content", {}).get("parts", []) or [])
    if cfg.provider == "openai":
        choices = data.get("choices") or []
        if not choices:
            raise MetaError("AI không trả về kết quả nào")
        return choices[0].get("message", {}).get("content") or ""
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _as_dict(raw) -> dict:
    """Chuỗi → dict. Vài model vẫn bọc JSON trong ```json dù đã ép schema."""
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.S)
    if m:
        text = m.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise MetaError(f"AI trả về dữ liệu không phải JSON: {text[:200]}") from e


def _friendly(e: httpx.HTTPStatusError) -> MetaError:
    code = e.response.status_code
    msg = {
        401: "API key không hợp lệ hoặc đã hết hạn",
        403: "API key không có quyền dùng model này",
        404: "Không tìm thấy model — kiểm tra lại model và base_url",
        422: "AI không tạo được dữ liệu đúng khuôn dạng yêu cầu",
        429: "Nhà cung cấp AI đang giới hạn tốc độ — thử lại sau ít phút",
    }.get(code)
    if msg is None:
        try:
            detail = e.response.text[:200]
        except Exception:      # noqa: BLE001
            detail = ""
        msg = ("Nhà cung cấp AI đang lỗi tạm thời — thử lại sau" if code >= 500
               else f"Lỗi gọi AI (HTTP {code}) {detail}")
    return MetaError(msg)


# ── Hàm chính ───────────────────────────────────────────────────────────────

async def suggest(cfg: LLMConfig, *, subtitle_text: str = "", keywords: str = "",
                  video_path: str = "", duration_ms: int = 0,
                  frames: list[bytes] | None = None, frame_count: int = FRAME_COUNT,
                  rules: Rules | None = None) -> dict:
    """Trả {"title": str, "description": str, "tags": list[str]}.

    Đưa `subtitle_text` thì AI đọc chữ. Đưa `video_path` mà không tự đưa `frames` thì hàm
    tự trích khung hình cho AI NHÌN — trích trong thread riêng để không chặn vòng lặp.

    Có cả hai là tốt nhất: chữ nói nội dung, hình nói bối cảnh.
    """
    if frames is None and video_path:
        frames = await asyncio.to_thread(extract_frames, video_path, duration_ms, frame_count)
    frames = frames or []

    system = _system(rules or Rules())
    prompt = build_prompt(subtitle_text, keywords, len(frames))
    url, headers, body = _build(cfg, system, prompt, frames)

    try:
        async with httpx.AsyncClient(timeout=cfg.timeout) as c:
            r = await c.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        raise _friendly(e) from e
    except httpx.HTTPError as e:
        raise MetaError(f"Không gọi được AI: {e}") from e

    log.info("video_meta_ai: %s/%s, %d khung hình, %d ký tự phụ đề",
             cfg.provider, cfg.model or "-", len(frames), len(subtitle_text))
    return sanitize(_as_dict(_extract(cfg, data)))


def suggest_sync(cfg: LLMConfig, **kw) -> dict:
    """Bản chặn, cho script hoặc worker đồng bộ. Đừng gọi trong code async."""
    return asyncio.run(suggest(cfg, **kw))


# ── Chạy thử từ dòng lệnh ───────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import os
    import sys

    ap = argparse.ArgumentParser(description="AI viết tiêu đề/mô tả/tag cho video")
    ap.add_argument("--video", default="", help="đường dẫn video (để AI nhìn khung hình)")
    ap.add_argument("--sub", default="", help="file .txt/.srt chứa phụ đề")
    ap.add_argument("--keywords", default="", help="từ khoá định hướng")
    ap.add_argument("--provider", default=os.getenv("LLM_PROVIDER", "anthropic"))
    ap.add_argument("--model", default=os.getenv("LLM_MODEL", ""))
    ap.add_argument("--base-url", default=os.getenv("LLM_BASE_URL", ""))
    ap.add_argument("--api-key", default=os.getenv("LLM_API_KEY", ""))
    a = ap.parse_args()

    if not a.video and not a.sub:
        sys.exit("Cần ít nhất --video hoặc --sub")

    text = ""
    if a.sub:
        text = open(a.sub, encoding="utf-8").read()
        if a.sub.lower().endswith(".srt"):
            # Bỏ số thứ tự và dòng thời gian, giữ lời thoại.
            text = "\n".join(ln for ln in text.splitlines()
                             if ln.strip() and "-->" not in ln and not ln.strip().isdigit())

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = LLMConfig(provider=a.provider, api_key=a.api_key, model=a.model, base_url=a.base_url)
    try:
        out = suggest_sync(cfg, subtitle_text=text, keywords=a.keywords, video_path=a.video)
    except MetaError as e:
        sys.exit(f"LỖI: {e}")
    print(json.dumps(out, ensure_ascii=False, indent=2))
