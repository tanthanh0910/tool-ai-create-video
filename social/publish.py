"""
Dang video len YouTube (resumable upload) va Facebook (Graph API).

Dang hong KHONG duoc keo ca luot xuat theo: video da render van con nguyen trong
output/ va van tai ve duoc, du token het han.
"""

import os
import re

import requests

from . import oauth, store

# Toi da 10 hashtag. Con so den tu YouTube: qua 15 hashtag thi YouTube bo qua
# TOAN BO hashtag cua video -> chua bien.
_MAX_HASHTAGS = 10

# Gioi han 1GB moi lan dang len Facebook. Lon hon can resumable upload,
# chua ho tro -> chan som kem thong bao ro.
_FB_MAX_BYTES = 1024 * 1024 * 1024

_CHUNK = 8 * 1024 * 1024  # 8MB

YOUTUBE_PRIVACY = ("public", "unlisted", "private")


class PublishError(Exception):
    """Loi co the hien thang cho user."""


# ---------- noi dung ----------

def normalize_hashtags(raw) -> list[str]:
    """Nhan list hoac chuoi ngan cach bang dau phay/khoang trang -> list '#tag'."""
    if isinstance(raw, str):
        parts = re.split(r"[,\s]+", raw)
    else:
        parts = list(raw or [])

    tags, seen = [], set()
    for p in parts:
        t = str(p).strip().lstrip("#")
        t = re.sub(r"[^0-9A-Za-zÀ-ỹ_]", "", t)
        # Hashtag khong phan biet hoa thuong tren ca hai nen tang -> #A va #a la mot
        if t and t.lower() not in seen:
            seen.add(t.lower())
            tags.append(f"#{t}")
    return tags[:_MAX_HASHTAGS]


def normalize_tags(raw) -> list[str]:
    """
    snippet.tags cua YouTube - nguoi xem KHONG thay, chi de tim kiem.
    Khac hoan toan voi hashtag trong mo ta.
    """
    if isinstance(raw, str):
        parts = raw.split(",")
    else:
        parts = list(raw or [])
    tags = []
    for p in parts:
        t = str(p).strip()
        if t and t not in tags:
            tags.append(t)
    return tags[:30]


def build_caption(title: str, description: str, hashtags: list[str]) -> str:
    """
    Facebook khong co truong tag cho video, va video doc bi xep thanh Reel khien
    title khong len feed -> phai gop title + description + hashtag vao MOT chuoi.
    """
    parts = [p.strip() for p in (title, description) if p and p.strip()]
    if hashtags:
        parts.append(" ".join(hashtags))
    return "\n\n".join(parts)


def build_youtube_description(description: str, hashtags: list[str]) -> str:
    text = (description or "").strip()
    if hashtags:
        text = (text + "\n\n" + " ".join(hashtags)).strip()
    return text[:5000]


# ---------- YouTube ----------

def publish_youtube(
    video_path: str,
    title: str,
    description: str = "",
    tags=None,
    hashtags=None,
    privacy: str = "private",
    on_progress=None,
) -> dict:
    """Resumable upload. Tra { video_id, url }."""
    if privacy not in YOUTUBE_PRIVACY:
        privacy = "private"
    if not os.path.exists(video_path):
        raise PublishError(f"Khong tim thay file: {video_path}")

    cfg = store.credentials("youtube")
    creds = store.app_credentials("youtube")
    if not creds:
        raise PublishError("Chua khai day du ung dung YouTube.")
    if not cfg.get("refresh_token"):
        raise PublishError("Chua ket noi YouTube.")

    client_id, client_secret = creds
    try:
        access_token = oauth.refresh_access_token(client_id, client_secret, cfg["refresh_token"])
    except oauth.OAuthError as e:
        raise PublishError(str(e))

    file_size = os.path.getsize(video_path)
    safe_title = re.sub(r"[<>]", "", (title or "Video").strip())[:100] or "Video"

    body = {
        "snippet": {
            "title": safe_title,
            "description": build_youtube_description(description, normalize_hashtags(hashtags)),
            "tags": normalize_tags(tags),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    # Buoc 1: mo phien, lay Location
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos",
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": "video/*",
        },
        json=body,
        timeout=60,
    )
    if init.status_code not in (200, 201):
        detail = oauth._err(oauth._json(init))
        if init.status_code == 403 and "quota" in detail.lower():
            # Quota mac dinh 10.000 don vi/ngay, moi videos.insert ton 1.600 -> ~6 video/ngay
            raise PublishError(
                f"Het quota YouTube hom nay (~6 video/ngay voi quota mac dinh). {detail}"
            )
        raise PublishError(f"Khong mo duoc phien upload: {detail}")

    upload_url = init.headers.get("Location")
    if not upload_url:
        raise PublishError("Google khong tra Location de upload.")

    # Buoc 2: PUT theo khoi 8MB
    uploaded = 0
    with open(video_path, "rb") as f:
        while uploaded < file_size:
            chunk = f.read(_CHUNK)
            if not chunk:
                break
            start = uploaded
            end = uploaded + len(chunk) - 1
            resp = requests.put(
                upload_url,
                headers={
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                },
                data=chunk,
                timeout=600,
            )
            if resp.status_code in (200, 201):
                data = oauth._json(resp)
                video_id = data.get("id")
                if not video_id:
                    raise PublishError("Upload xong nhung khong nhan duoc video ID.")
                if on_progress:
                    on_progress(file_size, file_size)
                return {
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "privacy": privacy,
                }
            if resp.status_code == 308:
                # Resume Incomplete - doc con tro that tu header Range
                rng = resp.headers.get("Range")
                if rng and "-" in rng:
                    try:
                        uploaded = int(rng.split("-")[1]) + 1
                    except ValueError:
                        uploaded = end + 1
                else:
                    uploaded = end + 1
                if on_progress:
                    on_progress(uploaded, file_size)
                continue
            raise PublishError(
                f"Upload that bai (HTTP {resp.status_code}): {oauth._err(oauth._json(resp))}"
            )

    raise PublishError("Upload ket thuc bat thuong, khong nhan duoc video ID.")


# ---------- TikTok ----------

# Quy tac chunk cua TikTok: toi thieu 5MB, toi da 64MB, chunk CUOI duoc phinh
# den 128MB. Video < 5MB phai gui nguyen 1 chunk. Toi da 1000 chunk.
_TT_MIN_CHUNK = 5 * 1024 * 1024
_TT_MAX_CHUNK = 64 * 1024 * 1024
_TT_CHUNK = 32 * 1024 * 1024
_TT_MAX_CHUNKS = 1000


def _tiktok_chunk_plan(video_size: int) -> tuple[int, int]:
    """
    Tra (chunk_size, total_chunk_count) dung luat TikTok.

    total_chunk_count = floor(video_size / chunk_size) -> chunk cuoi tu hut phan du,
    khong phai lam tron len. Tinh sai cho nay la loi hay gap nhat.
    """
    # Duoi 5MB: bat buoc gui nguyen mot chunk
    if video_size < _TT_MIN_CHUNK:
        return video_size, 1

    chunk = _TT_CHUNK
    count = video_size // chunk

    # File nho hon 1 chunk -> khai chunk_size bang chinh do dai file, dung khai
    # chunk_size lon hon file
    if count == 0:
        return video_size, 1

    # Qua 1000 chunk -> phong chunk len (tran 64MB)
    if count > _TT_MAX_CHUNKS:
        chunk = min(_TT_MAX_CHUNK, -(-video_size // _TT_MAX_CHUNKS))
        count = max(1, video_size // chunk)

    return chunk, count


def publish_tiktok(video_path: str, on_progress=None) -> dict:
    """
    Day video vao HOP THU (inbox) cua creator trong app TikTok (scope video.upload).

    KHONG kem duoc tieu de / mo ta / hashtag: che do nay de creator tu viet caption
    trong app TikTok. Doi lai khong bi TikTok ep private nhu che do dang truc tiep
    cua app chua qua audit.
    """
    if not os.path.exists(video_path):
        raise PublishError(f"Khong tim thay file: {video_path}")

    cfg = store.credentials("tiktok")
    creds = store.app_credentials("tiktok")
    if not creds:
        raise PublishError("Chua khai day du ung dung TikTok.")
    if not cfg.get("refresh_token"):
        raise PublishError("Chua ket noi TikTok.")

    client_key, client_secret = creds
    try:
        access_token, new_refresh = oauth.refresh_tiktok_token(
            client_key, client_secret, cfg["refresh_token"]
        )
    except oauth.OAuthError as e:
        raise PublishError(str(e))
    if new_refresh and new_refresh != cfg["refresh_token"]:
        store.rotate_refresh_token("tiktok", new_refresh)

    video_size = os.path.getsize(video_path)
    chunk_size, total_chunks = _tiktok_chunk_plan(video_size)

    # Buoc 1: mo phien, lay upload_url
    init = requests.post(
        f"{oauth.TIKTOK_API}/v2/post/publish/inbox/video/init/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json={
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
            }
        },
        timeout=60,
    )
    body = oauth._json(init)
    if init.status_code != 200 or (body.get("error") or {}).get("code") not in (None, "ok"):
        raise PublishError(f"TikTok tu choi mo phien upload: {oauth._tiktok_err(body)}")

    data = body.get("data") or {}
    upload_url = data.get("upload_url")
    publish_id = data.get("publish_id")
    if not upload_url or not publish_id:
        raise PublishError("TikTok khong tra upload_url / publish_id.")

    # Buoc 2: PUT tung chunk, TUAN TU (TikTok bat buoc)
    with open(video_path, "rb") as f:
        for i in range(total_chunks):
            start = i * chunk_size
            # Chunk cuoi hut het phan con lai
            end = video_size - 1 if i == total_chunks - 1 else start + chunk_size - 1
            f.seek(start)
            payload = f.read(end - start + 1)

            resp = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(payload)),
                    "Content-Range": f"bytes {start}-{end}/{video_size}",
                },
                data=payload,
                timeout=1800,
            )
            if resp.status_code not in (200, 201, 206):
                raise PublishError(
                    f"Upload chunk {i+1}/{total_chunks} that bai (HTTP {resp.status_code}): "
                    f"{resp.text[:200]}"
                )
            if on_progress:
                on_progress(end + 1, video_size)

    status, fail_reason = _tiktok_status(access_token, publish_id)
    if status == "FAILED":
        raise PublishError(f"TikTok xu ly that bai: {fail_reason or 'khong ro ly do'}")

    return {
        "publish_id": publish_id,
        "status": status,
        "url": "https://www.tiktok.com/",
        "draft": True,
    }


def _tiktok_status(access_token: str, publish_id: str) -> tuple[str, str]:
    """Tra (status, fail_reason). Loi khi tra cuu thi khong nem - upload da xong roi."""
    try:
        resp = requests.post(
            f"{oauth.TIKTOK_API}/v2/post/publish/status/fetch/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=30,
        )
        data = (oauth._json(resp).get("data") or {})
        return data.get("status", ""), data.get("fail_reason", "")
    except Exception:
        return "", ""


# ---------- Facebook ----------

def publish_facebook(
    video_path: str,
    title: str,
    description: str = "",
    hashtags=None,
) -> dict:
    """POST /{page_id}/videos. Tra { video_id, url }."""
    if not os.path.exists(video_path):
        raise PublishError(f"Khong tim thay file: {video_path}")

    file_size = os.path.getsize(video_path)
    if file_size > _FB_MAX_BYTES:
        raise PublishError(
            f"Video {file_size / 1024 / 1024:.0f} MB vuot gioi han 1 GB moi lan dang "
            f"len Facebook. Can resumable upload, tool chua ho tro."
        )

    cfg = store.credentials("facebook")
    page_id = cfg.get("page_id")
    page_token = cfg.get("page_access_token")
    if not page_id or not page_token:
        raise PublishError("Chua ket noi Facebook.")

    caption = build_caption(title, description, normalize_hashtags(hashtags))

    with open(video_path, "rb") as f:
        resp = requests.post(
            f"{oauth.GRAPH}/{page_id}/videos",
            data={"description": caption, "access_token": page_token},
            files={"source": (os.path.basename(video_path), f, "video/mp4")},
            timeout=1800,
        )

    body = oauth._json(resp)
    if resp.status_code != 200:
        raise PublishError(f"Facebook tu choi: {oauth._err(body)}")

    video_id = body.get("id")
    if not video_id:
        raise PublishError(f"Khong nhan duoc video ID tu Facebook: {body}")

    return {
        "video_id": video_id,
        # Bai dang qua /{page_id}/videos da la cong khai san (privacy: EVERYONE)
        "url": f"https://www.facebook.com/{video_id}",
    }
