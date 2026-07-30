"""
Goi THAT API roi ghi verified_at / verify_error.

configured (da dien du o) va verified_at (goi that API thanh cong tai dung moc do)
la hai muc trang thai khac nhau, khong duoc gop. UI luon hien kem gio, khong dung
dau tich vinh vien - token co the bi thu hoi bat cu luc nao.
"""

import requests

from . import oauth, store


def verify(provider: str) -> tuple[bool, str]:
    """Tra (ok, ten kenh/Trang hoac thong bao loi). Tu ghi ket qua vao store."""
    try:
        if provider == "youtube":
            name = _verify_youtube()
        else:
            name = _verify_facebook()
    except oauth.OAuthError as e:
        store.set_verify_error(provider, str(e))
        return False, str(e)
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        store.set_verify_error(provider, msg)
        return False, msg

    store.set_verified(provider, name)
    return True, name


def _verify_youtube() -> str:
    cfg = store.credentials("youtube")
    creds = store.app_credentials("youtube")
    if not creds:
        raise oauth.OAuthError("Chua khai day du ung dung YouTube.")
    if not cfg.get("refresh_token"):
        raise oauth.OAuthError("Chua ket noi YouTube.")

    client_id, client_secret = creds
    access_token = oauth.refresh_access_token(client_id, client_secret, cfg["refresh_token"])

    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet", "mine": "true"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    body = oauth._json(resp)
    if resp.status_code != 200:
        raise oauth.OAuthError(f"Khong doc duoc kenh: {oauth._err(body)}")

    items = body.get("items") or []
    if not items:
        raise oauth.OAuthError("Tai khoan khong con kenh YouTube nao.")

    channel_id = items[0]["id"]
    title = items[0].get("snippet", {}).get("title", "")

    # Kenh dang dang nhap phai trung dich dang da luu.
    saved = cfg.get("channel_id")
    if saved and saved != channel_id:
        raise oauth.OAuthError(
            f"Token dang tro toi kenh '{title}' chu khong phai kenh da luu. "
            f"Bam Ngat roi ket noi lai."
        )
    return title


def _verify_facebook() -> str:
    cfg = store.credentials("facebook")
    page_id = cfg.get("page_id")
    page_token = cfg.get("page_access_token")
    if not page_id or not page_token:
        raise oauth.OAuthError("Chua ket noi Facebook.")

    resp = requests.get(
        f"{oauth.GRAPH}/{page_id}",
        params={"fields": "id,name", "access_token": page_token},
        timeout=30,
    )
    body = oauth._json(resp)
    if resp.status_code != 200:
        raise oauth.OAuthError(f"Page token khong dung duoc: {oauth._err(body)}")
    return body.get("name", "")
