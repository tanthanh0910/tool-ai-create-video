"""
Luong OAuth cho YouTube / Facebook.

  FE bam Ket noi
    -> GET /api/me/channels/{provider}/connect   tra { url }, FE tu chuyen trinh duyet
    -> user dang nhap, chon kenh/Trang, cap quyen
    -> nen tang goi GET /api/me/channels/{provider}/callback?code=&state=
       doi code lay token -> luu -> verify ngay -> redirect ve UI

state la token ky, chua { p: provider }, han 10 phut. BAT BUOC: callback do trinh
duyet goi nen khong mang duoc header Authorization - danh tinh phai di kem trong state.
Doc ra phai kiem ca provider khop.
"""

import hashlib
import secrets

import requests
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import Config
from . import store

STATE_MAX_AGE = 600  # 10 phut
GRAPH_VERSION = "v21.0"
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
TIKTOK_API = "https://open.tiktokapis.com"

# video.upload = day video vao HOP THU (inbox) cua creator trong app TikTok. Ho bam vao
# thong bao de mo trinh chinh sua roi tu dang. KHONG phai muc "Ban nhap" cua TikTok Studio.
# KHONG dung video.publish: app chua qua audit thi TikTok EP moi bai ve private,
# nen dang truc tiep se ra video khong ai xem duoc.
TIKTOK_SCOPES = ["user.info.basic", "video.upload"]

# Thieu youtube.readonly thi khong doc duoc channels.list?mine=true de lay
# Channel ID + ten kenh -> bao insufficient permission.
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
FACEBOOK_SCOPES = ["pages_show_list", "pages_read_engagement", "pages_manage_posts"]


class OAuthError(Exception):
    """Loi co the hien thang cho user."""


# ---------- state ----------

def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(store.jwt_secret(), salt="social-oauth-state")


def make_state(provider: str) -> str:
    return _serializer().dumps({"p": provider})


def read_state(token: str, provider: str) -> None:
    """Nem OAuthError neu state hong, het han, hoac provider khong khop."""
    try:
        data = _serializer().loads(token, max_age=STATE_MAX_AGE)
    except SignatureExpired:
        raise OAuthError("Lien ket ket noi da het han (10 phut). Bam Ket noi lai.")
    except BadSignature:
        raise OAuthError("State khong hop le.")
    if data.get("p") != provider:
        raise OAuthError("State khong khop nen tang.")


def redirect_uri(provider: str) -> str:
    """Phai khai Y HET chuoi nay ben console cua Google / Meta."""
    return f"{Config.OAUTH_REDIRECT_BASE}/api/me/channels/{provider}/callback"


# ---------- authorize url ----------

def authorize_url(provider: str) -> str:
    creds = store.app_credentials(provider)
    if not creds:
        raise OAuthError(
            "Chua khai day du ung dung. Dien Client ID va Client Secret truoc khi ket noi."
        )
    client_id, _ = creds
    state = make_state(provider)

    if provider == "youtube":
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri(provider),
            "response_type": "code",
            "scope": " ".join(YOUTUBE_SCOPES),
            # Thieu 2 tham so nay thi Google KHONG tra refresh_token
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
        return "https://accounts.google.com/o/oauth2/v2/auth?" + _qs(params)

    if provider == "tiktok":
        # PKCE BAT BUOC voi app Desktop. Phai khai app dang Desktop chu khong phai
        # Web: Web Login Kit bat redirect_uri phai HTTPS, localhost khong dung duoc.
        verifier = _new_code_verifier()
        store.merge("tiktok", {"pkce_verifier": verifier})
        params = {
            "client_key": client_id,
            "response_type": "code",
            "scope": ",".join(TIKTOK_SCOPES),
            "redirect_uri": redirect_uri(provider),
            "state": state,
            # TikTok doi code_challenge la SHA256 ma hoa HEX. Chuan OAuth dung
            # base64url - dung base64url o day se bi tu choi.
            "code_challenge": hashlib.sha256(verifier.encode()).hexdigest(),
            "code_challenge_method": "S256",
        }
        return "https://www.tiktok.com/v2/auth/authorize/?" + _qs(params)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(provider),
        "response_type": "code",
        "scope": ",".join(FACEBOOK_SCOPES),
        "state": state,
    }
    return f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth?" + _qs(params)


def _new_code_verifier() -> str:
    """Chuoi ngau nhien 43-128 ky tu trong tap [A-Za-z0-9-._~]."""
    return secrets.token_urlsafe(64)[:96]


def _qs(params: dict) -> str:
    from urllib.parse import urlencode
    return urlencode(params)


# ---------- doi code lay token ----------

def exchange_youtube(code: str) -> dict:
    """
    code -> refresh_token, roi doc channels.list?mine=true de lay dich dang.
    Tra dict de merge thang vao store.
    """
    creds = store.app_credentials("youtube")
    if not creds:
        raise OAuthError("Chua khai day du ung dung YouTube.")
    client_id, client_secret = creds

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri("youtube"),
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    body = _json(resp)
    if resp.status_code != 200:
        raise OAuthError(f"Google tu choi doi code: {_err(body)}")

    refresh_token = body.get("refresh_token")
    access_token = body.get("access_token")
    if not refresh_token:
        raise OAuthError(
            "Google khong tra refresh_token. Vao Tai khoan Google > Quyen truy cap "
            "cua ben thu ba, go ung dung nay ra roi ket noi lai."
        )

    channel_id, channel_title = _youtube_channel(access_token)
    return {
        "refresh_token": refresh_token,
        "channel_id": channel_id,
        "channel_title": channel_title,
    }


def _youtube_channel(access_token: str) -> tuple[str, str]:
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet", "mine": "true"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    body = _json(resp)
    if resp.status_code != 200:
        raise OAuthError(f"Khong doc duoc kenh YouTube: {_err(body)}")
    items = body.get("items") or []
    if not items:
        raise OAuthError(
            "Tai khoan Google nay chua co kenh YouTube nao. Tao kenh roi ket noi lai."
        )
    item = items[0]
    return item["id"], item.get("snippet", {}).get("title", "")


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """Moi lan dang: doi refresh_token -> access_token roi moi upload."""
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    body = _json(resp)
    if resp.status_code != 200:
        detail = _err(body)
        if "invalid_grant" in detail:
            # App o che do Testing thi Google thu hoi refresh token sau dung 7 ngay.
            raise OAuthError(
                "Token da bi thu hoi (invalid_grant). Neu app dang o che do Testing, "
                "vao Google Auth Platform > Audience > Publish app roi ket noi lai."
            )
        raise OAuthError(f"Khong lam moi duoc token: {detail}")
    return body["access_token"]


def exchange_facebook(code: str) -> dict:
    """
    code -> user token ngan han -> token dai han (60 ngay) -> Page token (khong han).
    Lam het trong mot cu bam.
    """
    creds = store.app_credentials("facebook")
    if not creds:
        raise OAuthError("Chua khai day du ung dung Facebook.")
    app_id, app_secret = creds

    # Buoc 1: code -> user token ngan han
    resp = requests.get(
        f"{GRAPH}/oauth/access_token",
        params={
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_uri("facebook"),
            "code": code,
        },
        timeout=30,
    )
    body = _json(resp)
    if resp.status_code != 200:
        raise OAuthError(f"Facebook tu choi doi code: {_err(body)}")
    short_token = body["access_token"]

    # Buoc 2: token ngan han -> token dai han (60 ngay)
    resp = requests.get(
        f"{GRAPH}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
        timeout=30,
    )
    body = _json(resp)
    if resp.status_code != 200:
        raise OAuthError(f"Khong doi duoc token dai han: {_err(body)}")
    long_token = body["access_token"]

    # Buoc 3: chon Trang -> Page token (khong han)
    hint = (store.get("facebook").get("page_id_hint") or "").strip()
    page_id, page_name, page_token = _pick_facebook_page(long_token, hint)

    return {
        "page_access_token": page_token,
        "page_id": page_id,
        "page_name": page_name,
    }


def _pick_facebook_page(user_token: str, hint: str) -> tuple[str, str, str]:
    """
    4 nhanh, theo dung thu tu:

      1. co hint & hint nam trong me/accounts  -> lay Trang do
      2. co hint & khong nam (ke ca list rong) -> GET /{hint}?fields=access_token
                                                  that bai -> loi ro rang
      3. khong hint & me/accounts tra NHIEU    -> LOI, liet ke ten + ID tung Trang
      4. khong hint & dung 1 Trang             -> lay Trang do
         khong hint & rong                     -> LOI "khong liet ke Trang nao"
    """
    pages = _facebook_accounts(user_token)

    if hint:
        for p in pages:
            if str(p.get("id")) == hint:
                return str(p["id"]), p.get("name", ""), p["access_token"]

        # Nhanh 2 BAT BUOC: me/accounts la lenh liet ke va hay tra rong voi Trang
        # thuoc Business Portfolio, ke ca khi user da tick dung Trang va quyen du
        # granted. Duong tin cay duy nhat la biet truoc Page ID roi hoi thang.
        resp = requests.get(
            f"{GRAPH}/{hint}",
            params={"fields": "id,name,access_token", "access_token": user_token},
            timeout=30,
        )
        body = _json(resp)
        if resp.status_code != 200 or not body.get("access_token"):
            raise OAuthError(
                f"Khong lay duoc quyen dang cho Trang ID '{hint}'. "
                f"Kiem tra lai ID va chac chan ban la quan tri vien cua Trang. "
                f"Chi tiet: {_err(body)}"
            )
        return str(body["id"]), body.get("name", ""), body["access_token"]

    if len(pages) > 1:
        # Tuyet doi khong lay bua pages[0]: user quan tri nhieu Trang se dang nham
        # ma khong co dau hieu nao.
        listing = ", ".join(f"{p.get('name', '?')} (ID {p.get('id')})" for p in pages)
        raise OAuthError(
            f"Ban quan tri {len(pages)} Trang. Dien Page ID vao o 'Page ID goi y' "
            f"roi ket noi lai de chon dung Trang. Cac Trang: {listing}"
        )

    if len(pages) == 1:
        p = pages[0]
        return str(p["id"]), p.get("name", ""), p["access_token"]

    raise OAuthError(
        "Facebook khong liet ke Trang nao. Neu Trang thuoc Business Portfolio thi "
        "me/accounts hay tra rong - dien Page ID vao o 'Page ID goi y' roi ket noi lai."
    )


def exchange_tiktok(code: str) -> dict:
    """
    code + code_verifier -> refresh_token (365 ngay) + open_id.

    access_token chi song 24h nen khong luu; moi lan dang lai doi tu refresh_token.
    """
    creds = store.app_credentials("tiktok")
    if not creds:
        raise OAuthError("Chua khai day du ung dung TikTok.")
    client_key, client_secret = creds

    verifier = store.credentials("tiktok").get("pkce_verifier")
    if not verifier:
        raise OAuthError(
            "Mat code_verifier cua PKCE. Bam Ket noi lai (dung mo lai lien ket cu)."
        )

    resp = requests.post(
        f"{TIKTOK_API}/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri("tiktok"),
            "code_verifier": verifier,
        },
        timeout=30,
    )
    body = _json(resp)
    # TikTok tra loi ngay trong body ke ca khi HTTP 200 -> phai kiem ca hai
    if resp.status_code != 200 or body.get("error"):
        raise OAuthError(f"TikTok tu choi doi code: {_tiktok_err(body)}")

    refresh_token = body.get("refresh_token")
    access_token = body.get("access_token")
    open_id = body.get("open_id")
    if not refresh_token or not open_id:
        raise OAuthError("TikTok khong tra refresh_token hoac open_id.")

    display_name = _tiktok_display_name(access_token) if access_token else ""

    # Dung xong verifier thi xoa ngay
    store.merge("tiktok", {"pkce_verifier": ""})

    return {
        "refresh_token": refresh_token,
        "open_id": open_id,
        "display_name": display_name,
    }


def refresh_tiktok_token(client_key: str, client_secret: str, refresh_token: str) -> tuple[str, str | None]:
    """
    Doi refresh_token -> (access_token, refresh_token moi neu co).

    TikTok co the tra refresh_token moi -> phai luu lai, khong thi sau 365 ngay chet.
    """
    resp = requests.post(
        f"{TIKTOK_API}/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    body = _json(resp)
    if resp.status_code != 200 or body.get("error"):
        raise OAuthError(
            f"Khong lam moi duoc token TikTok: {_tiktok_err(body)}. "
            f"Neu refresh_token da qua 365 ngay thi phai ket noi lai."
        )
    return body["access_token"], body.get("refresh_token")


def _tiktok_display_name(access_token: str) -> str:
    """Ban de dai: khong lay duoc ten thi tra rong chu khong lam hong ca luot ket noi."""
    try:
        return tiktok_user(access_token).get("display_name", "")
    except OAuthError:
        return ""


def tiktok_user(access_token: str) -> dict:
    """open_id + display_name. Nem OAuthError neu token khong dung duoc."""
    resp = requests.get(
        f"{TIKTOK_API}/v2/user/info/",
        params={"fields": "open_id,display_name"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    body = _json(resp)
    if resp.status_code != 200 or (body.get("error") or {}).get("code") not in (None, "ok"):
        raise OAuthError(f"Khong doc duoc tai khoan TikTok: {_tiktok_err(body)}")
    return ((body.get("data") or {}).get("user") or {})


def _tiktok_err(body: dict) -> str:
    """TikTok co 2 dang loi: {error, error_description} va {error: {code, message}}."""
    if not body:
        return "khong doc duoc phan hoi"
    err = body.get("error")
    if isinstance(err, dict):
        return err.get("message") or err.get("code") or str(err)
    if isinstance(err, str):
        return f"{err}: {body.get('error_description', '')}".strip(": ")
    return str(body)[:300]


def _facebook_accounts(user_token: str) -> list[dict]:
    resp = requests.get(
        f"{GRAPH}/me/accounts",
        params={"fields": "id,name,access_token", "access_token": user_token},
        timeout=30,
    )
    body = _json(resp)
    if resp.status_code != 200:
        raise OAuthError(f"Khong doc duoc danh sach Trang: {_err(body)}")
    return body.get("data") or []


# ---------- helper ----------

def _json(resp) -> dict:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _err(body: dict) -> str:
    if not body:
        return "khong doc duoc phan hoi"
    err = body.get("error")
    if isinstance(err, dict):
        return err.get("message") or str(err)
    if isinstance(err, str):
        return f"{err}: {body.get('error_description', '')}".strip(": ")
    return str(body)[:300]
