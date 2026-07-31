"""
Flask Blueprint: 7 endpoint cau hinh kenh + dang bai.

Ban goc chay tren FastAPI nhieu user (moi user 1 hang trong DB). Tool nay chay
local 1 nguoi dung nen bo lop Authorization, con lai giu nguyen hop dong API.
"""

import json
import os
from urllib.parse import urlencode

from flask import Blueprint, Response, redirect, request

from config import Config
from video_meta_ai import LLMConfig, MetaError, suggest_sync
from . import oauth, publish as publisher, store, verify as verifier

bp = Blueprint("social", __name__)

PROVIDERS = ("youtube", "facebook", "tiktok")
PROVIDER_LABEL = {"youtube": "YouTube", "facebook": "Facebook", "tiktok": "TikTok"}


def _bad(msg: str, code: int = 400):
    return {"error": msg}, code


def _check_provider(provider: str):
    if provider not in PROVIDERS:
        return _bad(f"Nen tang khong ho tro: {provider}", 404)
    return None


# ---------- 1. Doc cau hinh ----------

@bp.route("/api/me/channels", methods=["GET"])
def get_channels():
    """Cau hinh cua minh, DA LOC bi mat."""
    return {p: store.to_public(p) for p in PROVIDERS}


@bp.route("/api/me/channels/available", methods=["GET"])
def channels_available():
    """
    {ready, redirect_uri} moi nen tang.
    redirect_uri phai hien ra UI kem nut copy - go tay chuoi nay la nguon loi so
    mot, ma ca hai nen tang chi bao redirect_uri_mismatch chu khong noi sai o dau.
    """
    out = {}
    for p in PROVIDERS:
        out[p] = {
            "ready": store.app_credentials(p) is not None,
            "redirect_uri": oauth.redirect_uri(p),
        }
    return out


# ---------- 2. Khai app ----------

@bp.route("/api/me/channels/<provider>/app", methods=["PUT"])
def put_app(provider):
    err = _check_provider(provider)
    if err:
        return err

    data = request.json or {}
    patch = {}

    if provider == "youtube":
        allowed = ("client_id", "client_secret")
    elif provider == "facebook":
        allowed = ("app_id", "app_secret", "page_id_hint")
    else:
        allowed = ("client_key", "client_secret")

    for field in allowed:
        if field in data:
            value = data[field]
            # Quy uoc PATCH: vang mat/None = giu nguyen, "" = xoa, co gia tri = thay moi
            patch[field] = None if value is None else str(value).strip()

    if not patch:
        return _bad("Khong co truong nao de cap nhat")

    store.merge(provider, patch)
    return store.to_public(provider)


# ---------- 3. OAuth ----------

@bp.route("/api/me/channels/<provider>/connect", methods=["GET"])
def connect(provider):
    err = _check_provider(provider)
    if err:
        return err
    try:
        return {"url": oauth.authorize_url(provider)}
    except oauth.OAuthError as e:
        return _bad(str(e))


@bp.route("/api/me/channels/<provider>/callback", methods=["GET"])
def callback(provider):
    """Nen tang goi ve day. Doi code lay token -> luu -> verify ngay -> redirect ra UI."""
    if provider not in PROVIDERS:
        return _ui_redirect("error", f"Nen tang khong ho tro: {provider}")

    # KHONG log code / state / token o day.
    if request.args.get("error"):
        desc = request.args.get("error_description") or request.args.get("error")
        return _ui_redirect("error", f"{PROVIDER_LABEL[provider]} tu choi: {desc}")

    code = request.args.get("code")
    state = request.args.get("state")
    if not code or not state:
        return _ui_redirect("error", "Callback thieu code hoac state.")

    try:
        oauth.read_state(state, provider)
    except oauth.OAuthError as e:
        return _ui_redirect("error", str(e))

    try:
        if provider == "youtube":
            result = oauth.exchange_youtube(code)
            new_target, old_target = result["channel_id"], store.get(provider).get("channel_id")
            new_name = result.get("channel_title", "")
            old_name = store.get(provider).get("channel_title", "")
        elif provider == "facebook":
            result = oauth.exchange_facebook(code)
            new_target, old_target = result["page_id"], store.get(provider).get("page_id")
            new_name = result.get("page_name", "")
            old_name = store.get(provider).get("page_name", "")
        else:
            result = oauth.exchange_tiktok(code)
            new_target, old_target = result["open_id"], store.get(provider).get("open_id")
            new_name = result.get("display_name", "")
            old_name = store.get(provider).get("display_name", "")
    except oauth.OAuthError as e:
        return _ui_redirect("error", str(e))
    except Exception as e:
        return _ui_redirect("error", f"Loi khi doi token: {type(e).__name__}: {e}")

    # Ket noi lai phai trung dung kenh cu. Khong chan thi user dang dang nhap tai
    # khoan khac se am tham thay kenh: badge van xanh, video sau do len sai cho -
    # loai loi chi phat hien khi da dang nham.
    if old_target and new_target != old_target:
        return _ui_redirect(
            "error",
            f"Tai khoan nay tro toi '{new_name or new_target}' chu khong phai "
            f"'{old_name or old_target}' da ket noi truoc do. Bam Ngat truoc neu "
            f"that su muon doi kenh.",
        )

    store.merge(provider, result)

    ok, detail = verifier.verify(provider)
    if ok:
        return _ui_redirect("success", f"Da ket noi {PROVIDER_LABEL[provider]}: {detail}")
    return _ui_redirect("warning", f"Da luu token nhung kiem tra that bai: {detail}")


def _ui_redirect(status: str, msg: str):
    return redirect(f"/?{urlencode({'tab': 'channels', 'status': status, 'msg': msg})}")


# ---------- 4. Ngat ket noi ----------

@bp.route("/api/me/channels/<provider>", methods=["DELETE"])
def delete_channel(provider):
    err = _check_provider(provider)
    if err:
        return err
    store.disconnect(provider)
    return store.to_public(provider)


@bp.route("/api/me/channels/<provider>/verify", methods=["POST"])
def verify_channel(provider):
    err = _check_provider(provider)
    if err:
        return err
    ok, detail = verifier.verify(provider)
    return {"ok": ok, "detail": detail, **store.to_public(provider)}


# ---------- 5. Danh sach video da render ----------

@bp.route("/api/outputs", methods=["GET"])
def list_outputs():
    out_dir = Config.OUTPUT_DIR
    if not os.path.isdir(out_dir):
        return {"files": []}

    files = []
    for name in os.listdir(out_dir):
        path = os.path.join(out_dir, name)
        if not os.path.isfile(path) or not name.lower().endswith(".mp4"):
            continue
        stat = os.stat(path)
        files.append({
            "path": os.path.join(out_dir, name),
            "name": name,
            "size_mb": round(stat.st_size / 1024 / 1024, 1),
            "mtime": stat.st_mtime,
        })
    files.sort(key=lambda f: f["mtime"], reverse=True)
    return {"files": files}


# ---------- 6. AI viet title / description / tags ----------

@bp.route("/api/publish-meta/suggest", methods=["POST"])
def suggest_meta():
    """
    AI viet title/description/tags — dung video_meta_ai.py (module doc lap).

    Video cua tool nay KHONG co phu de (chi TTS doc ten loai), nen duong chinh la
    cho AI NHIN khung hinh trich tu chinh video. `keywords` chi de DINH HUONG:
    khop thi dung, khong khop thi module tu bo qua chu khong bia noi dung.
    """
    data = request.json or {}
    file_path = (data.get("file") or "").strip()
    keywords = (data.get("keywords") or "").strip()
    subtitle = (data.get("subtitle") or "").strip()

    if not Config.LLM_API_KEY:
        return _bad(
            f"Chua khai LLM_API_KEY trong file .env "
            f"(provider dang chon: {Config.LLM_PROVIDER}).", 503
        )

    video_path = ""
    if file_path:
        video_path = _safe_output_path(file_path) or ""
        if not video_path:
            return _bad("File khong nam trong thu muc output/ hoac khong ton tai")

    if not video_path and not subtitle:
        return _bad("Chon video de AI xem khung hinh, hoac dua vao phu de")

    cfg = LLMConfig(
        provider=Config.LLM_PROVIDER,
        api_key=Config.LLM_API_KEY,
        model=Config.LLM_MODEL,
        base_url=Config.LLM_BASE_URL,
    )

    try:
        meta = suggest_sync(
            cfg,
            subtitle_text=subtitle,
            keywords=keywords,
            video_path=video_path,
            frame_count=Config.LLM_FRAME_COUNT,
        )
    except MetaError as e:
        # MetaError da la cau tieng Viet doc duoc - hien thang len UI, khong lo chi tiet noi bo
        return _bad(str(e), 502)
    except Exception as e:
        return _bad(f"Loi goi AI: {type(e).__name__}: {e}", 502)

    tags = publisher.normalize_tags(meta.get("tags"))
    return {
        "title": meta.get("title", ""),
        "description": meta.get("description", ""),
        "tags": tags,
        "hashtags": _hashtags_from_tags(tags),
        "model": f"{cfg.provider}/{cfg.model or 'mac dinh'}",
    }


def _hashtags_from_tags(tags: list[str], limit: int = 5) -> list[str]:
    """
    video_meta_ai chi tra `tags` (tu khoa tim kiem, nguoi xem khong thay).
    Suy ra hashtag tu cac tag NGAN (<=2 tu) bang cach bo khoang trang; tag dai
    bien thanh hashtag khong ai go nen bo qua. Giu it thoi - publish.py cap 10,
    va qua 15 hashtag thi YouTube bo qua TOAN BO hashtag cua video.
    """
    out = []
    for t in tags:
        if len(t.split()) > 2:
            continue
        h = t.replace(" ", "")
        if h and h not in out:
            out.append(h)
        if len(out) >= limit:
            break
    return out


# ---------- 7. Dang bai ----------

@bp.route("/api/publish", methods=["POST"])
def publish():
    """
    Dang 1 video len cac kenh da chon. Stream tien trinh qua SSE.

    Noi dung rieng cho tung kenh: mac dinh dung chung, tach khi can.
    Body:
      {
        "file": "./output/01_xxx.mp4",
        "channels": ["youtube", "facebook"],
        "privacy": "private" | "unlisted" | "public",
        "shared": {"title": "...", "description": "...", "tags": [...], "hashtags": [...]},
        "per_channel": {"facebook": {"title": "...", ...}}   // tuy chon
      }
    """
    data = request.json or {}
    file_path = (data.get("file") or "").strip()
    channels = [c for c in (data.get("channels") or []) if c in PROVIDERS]
    privacy = data.get("privacy") or "private"
    shared = data.get("shared") or {}
    per_channel = data.get("per_channel") or {}

    def stream_error(msg):
        def gen():
            yield _sse({"type": "error", "message": msg})
        return Response(gen(), mimetype="text/event-stream")

    if not file_path:
        return stream_error("Chua chon video de dang")
    if not channels:
        return stream_error("Chua chon kenh nao")

    safe_path = _safe_output_path(file_path)
    if not safe_path:
        return stream_error("File khong nam trong thu muc output/ hoac khong ton tai")

    def generate():
        size_mb = os.path.getsize(safe_path) / 1024 / 1024
        yield _sse({"type": "log", "message": f"📤 Dang: {os.path.basename(safe_path)} ({size_mb:.1f} MB)"})
        yield _sse({"type": "progress", "percent": 5})

        results = []
        step = 90 / len(channels)

        for i, provider in enumerate(channels):
            label = PROVIDER_LABEL[provider]
            base_pct = 5 + i * step

            content = {**shared, **(per_channel.get(provider) or {})}
            title = (content.get("title") or os.path.splitext(os.path.basename(safe_path))[0]).strip()

            if not store.is_connected(provider):
                msg = f"Chua ket noi {label} - bo qua"
                yield _sse({"type": "log", "message": f"  ⚠ {msg}", "level": "warn"})
                results.append({"provider": provider, "ok": False, "error": msg})
                continue

            yield _sse({"type": "log", "message": f"  [{i+1}/{len(channels)}] Dang len {label}..."})

            try:
                if provider == "youtube":
                    result = publisher.publish_youtube(
                        safe_path,
                        title=title,
                        description=content.get("description", ""),
                        tags=content.get("tags"),
                        hashtags=content.get("hashtags"),
                        privacy=privacy,
                    )
                    yield _sse({
                        "type": "log",
                        "message": f"  ✓ {label} ({result['privacy']}): {result['url']}",
                        "level": "success",
                    })
                elif provider == "facebook":
                    result = publisher.publish_facebook(
                        safe_path,
                        title=title,
                        description=content.get("description", ""),
                        hashtags=content.get("hashtags"),
                    )
                    yield _sse({
                        "type": "log",
                        "message": f"  ✓ {label}: {result['url']}",
                        "level": "success",
                    })
                else:
                    result = publisher.publish_tiktok(safe_path)
                    # Che do Drafts KHONG gui kem caption duoc - creator tu viet trong
                    # app TikTok. Nen in caption ra day de copy cho khoi phai go lai.
                    caption = publisher.build_caption(
                        title,
                        content.get("description", ""),
                        publisher.normalize_hashtags(content.get("hashtags")),
                    )
                    yield _sse({
                        "type": "log",
                        "message": f"  ✓ {label}: da vao HOP THU app TikTok (status={result['status'] or '?'})",
                        "level": "success",
                    })
                    yield _sse({
                        "type": "log",
                        "message": "  📱 Mo app TikTok tren DIEN THOAI > tab Hop thu > bam vao thong bao de dang. KHONG nam o muc Ban nhap.",
                        "level": "warn",
                    })
                    if caption:
                        yield _sse({"type": "log", "message": "  📋 Caption de copy vao app:"})
                        for line in caption.splitlines():
                            yield _sse({"type": "log", "message": f"     {line}"})
                    result["caption"] = caption
                results.append({"provider": provider, "ok": True, **result})
            except publisher.PublishError as e:
                # Dang hong khong keo ca luot theo: file van con trong output/
                yield _sse({"type": "log", "message": f"  ✗ {label}: {e}", "level": "error"})
                results.append({"provider": provider, "ok": False, "error": str(e)})
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                yield _sse({"type": "log", "message": f"  ✗ {label}: {msg}", "level": "error"})
                results.append({"provider": provider, "ok": False, "error": msg})

            yield _sse({"type": "progress", "percent": base_pct + step})

        ok_count = sum(1 for r in results if r["ok"])
        yield _sse({"type": "progress", "percent": 100})
        yield _sse({
            "type": "done",
            "message": f"Dang xong {ok_count}/{len(channels)} kenh",
            "results": results,
            "files": [],
        })

    return Response(generate(), mimetype="text/event-stream")


def _safe_output_path(file_path: str) -> str | None:
    """Chi cho phep file nam THUC SU trong output/ (chan ../ di ra ngoai)."""
    out_dir = os.path.realpath(Config.OUTPUT_DIR)
    target = os.path.realpath(file_path)
    if os.path.commonpath([out_dir, target]) != out_dir:
        return None
    if not os.path.isfile(target):
        return None
    return target


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
