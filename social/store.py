"""
Luu tru cau hinh kenh dang bai.

Ban goc dung cot JSONB users.social_channels. Tool nay chay local, 1 nguoi dung,
khong co database -> luu vao 1 file JSON co cung hinh dang du lieu.

Ba quy uoc bat buoc giu (chep tu thiet ke goc):
  1. to_public() chi tra truong cong khai + co <ten>_set. Khong bao gio tra bi mat.
     credentials() giai ma, chi goi o tang publish/verify.
  2. PATCH bi mat: vang mat/None = giu nguyen, "" = xoa, co gia tri = thay moi.
  3. Ghi la ghi ca dict roi save() - khong sua tai cho roi quen luu.

Tach hai muc trang thai, KHONG gop:
  - configured = da dien du o (chuoi rac van tinh)
  - verified_at = da goi that API va thanh cong tai dung moc do
"""

import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken

from config import Config

PROVIDERS = ("youtube", "facebook")

# Truong bi mat -> luu duoi dang Fernet
SECRET_FIELDS = {
    "youtube": ("client_secret", "refresh_token"),
    "facebook": ("app_secret", "page_access_token"),
}

# Truong cong khai -> tra thang ra API
PUBLIC_FIELDS = {
    "youtube": (
        "client_id", "channel_id", "channel_title",
        "verified_at", "verify_error", "verified_name", "updated_at",
    ),
    "facebook": (
        "app_id", "page_id", "page_id_hint", "page_name",
        "verified_at", "verify_error", "verified_name", "updated_at",
    ),
}

# Doi mot trong nhung truong nay = trang thai verify cu khong con y nghia.
# Facebook CHI co page_id/page_access_token: Page token tu mang danh tinh app
# ben trong, doi app_id/app_secret khong lam no hong -> xoa verify se la bao dong sai.
INVALIDATING_FIELDS = {
    "youtube": ("channel_id", "client_id", "client_secret", "refresh_token"),
    "facebook": ("page_id", "page_access_token"),
}

# Du de coi la "da khai app" (buoc Ket noi mo khoa)
APP_FIELDS = {
    "youtube": ("client_id", "client_secret"),
    "facebook": ("app_id", "app_secret"),
}

# Du de coi la "da ket noi" (dang duoc bai)
CONNECTED_FIELDS = {
    "youtube": ("refresh_token", "channel_id"),
    "facebook": ("page_access_token", "page_id"),
}

# Ngat ket noi xoa token nhung GIU app da khai - neu xoa sach thi moi lan Ngat
# user phai di lay lai Client ID ben Google Cloud.
DISCONNECT_CLEARS = {
    "youtube": ("refresh_token", "channel_id", "channel_title",
                "verified_at", "verify_error", "verified_name"),
    "facebook": ("page_access_token", "page_id", "page_name",
                 "verified_at", "verify_error", "verified_name"),
}

_SECRET_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".jwt_secret"
)


# ---------- Khoa ----------

def jwt_secret() -> str:
    """
    Khoa ky state + dan xuat khoa Fernet.

    Uu tien JWT_SECRET trong .env. Neu chua khai thi sinh 1 lan roi ghi ra
    file .jwt_secret (da gitignore) - de token khong chet moi lan restart server.
    """
    if Config.JWT_SECRET:
        return Config.JWT_SECRET

    if os.path.exists(_SECRET_FILE):
        with open(_SECRET_FILE) as f:
            saved = f.read().strip()
            if saved:
                return saved

    generated = secrets.token_urlsafe(48)
    with open(_SECRET_FILE, "w") as f:
        f.write(generated)
    os.chmod(_SECRET_FILE, 0o600)
    print("  [social] Da sinh JWT_SECRET moi -> .jwt_secret")
    return generated


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(jwt_secret().encode()).digest())
    return Fernet(key)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str | None:
    """Tra None neu khong giai ma duoc (thuong la do JWT_SECRET da doi)."""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, Exception):
        return None


# ---------- Doc / ghi file ----------

def _path() -> str:
    p = Config.CHANNELS_FILE
    if not os.path.isabs(p):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = os.path.join(base, p)
    return p


def load_all() -> dict:
    path = _path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [social] Khong doc duoc {path}: {e}")
        return {}


def save_all(data: dict) -> None:
    path = _path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    os.chmod(path, 0o600)


def get(provider: str) -> dict:
    return load_all().get(provider, {})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------- Trang thai ----------

def is_configured(provider: str) -> bool:
    """Da dien du o khai app chua. Chuoi rac van tinh la da dien."""
    cfg = get(provider)
    return all(cfg.get(f) for f in APP_FIELDS[provider])


def is_connected(provider: str) -> bool:
    cfg = get(provider)
    return all(cfg.get(f) for f in CONNECTED_FIELDS[provider])


def to_public(provider: str) -> dict:
    """
    Cau hinh da loc bi mat - dung cho API tra ve FE.
    Bi mat chi lo ra duoi dang co <ten>_set: true/false.
    """
    cfg = get(provider)
    out = {f: cfg.get(f, "") for f in PUBLIC_FIELDS[provider]}
    for f in SECRET_FIELDS[provider]:
        out[f"{f}_set"] = bool(cfg.get(f))
    out["configured"] = is_configured(provider)
    out["connected"] = is_connected(provider)
    return out


def credentials(provider: str) -> dict:
    """Ban da giai ma. CHI goi o tang verify/publish, khong bao gio tra ra API."""
    cfg = dict(get(provider))
    for f in SECRET_FIELDS[provider]:
        if cfg.get(f):
            cfg[f] = decrypt(cfg[f])
    return cfg


def app_credentials(provider: str) -> tuple[str, str] | None:
    """
    (client_id, client_secret) de chay OAuth.

    Uu tien app cua user. Neu user chua khai gi thi lui ve app he thong trong env.
    Nhung khai do dang (co ID, mat secret) thi tra None chu KHONG lui - chay OAuth
    duoi client cua user ma chua dang ky redirect_uri chi ra redirect_uri_mismatch
    o phia Google/Meta, loi do khong chi nguoc ve duoc.
    """
    cfg = credentials(provider)
    id_field, secret_field = APP_FIELDS[provider]
    user_id = cfg.get(id_field) or ""
    user_secret = cfg.get(secret_field) or ""

    if user_id and user_secret:
        return user_id, user_secret
    if user_id or user_secret:
        return None  # khai do dang -> khong lui

    if provider == "youtube":
        sys_id, sys_secret = Config.YOUTUBE_CLIENT_ID, Config.YOUTUBE_CLIENT_SECRET
    else:
        sys_id, sys_secret = Config.FACEBOOK_APP_ID, Config.FACEBOOK_APP_SECRET

    if sys_id and sys_secret:
        return sys_id, sys_secret
    return None


# ---------- Ghi ----------

def merge(provider: str, patch: dict) -> dict:
    """
    Ap patch vao cau hinh hien co.

    Quy uoc bi mat: vang mat/None = giu nguyen, "" = xoa, co gia tri = thay moi.
    Doi truong invalidating -> xoa trang thai verify (khong con dung nua).
    """
    data = load_all()
    cfg = dict(data.get(provider, {}))
    before = {f: cfg.get(f) for f in INVALIDATING_FIELDS[provider]}

    for field, value in patch.items():
        if value is None:
            continue  # giu nguyen
        if field in SECRET_FIELDS[provider]:
            if value == "":
                cfg.pop(field, None)
            else:
                cfg[field] = encrypt(value)
        else:
            if value == "":
                cfg.pop(field, None)
            else:
                cfg[field] = value

    after = {f: cfg.get(f) for f in INVALIDATING_FIELDS[provider]}
    # So sanh o dang da ma hoa cung duoc: gia tri moi luon ra ciphertext khac
    if before != after:
        for f in ("verified_at", "verify_error", "verified_name"):
            cfg.pop(f, None)

    cfg["updated_at"] = _now()
    data[provider] = cfg
    save_all(data)
    return cfg


def set_verified(provider: str, name: str) -> None:
    data = load_all()
    cfg = dict(data.get(provider, {}))
    cfg["verified_at"] = _now()
    cfg["verified_name"] = name
    cfg["verify_error"] = ""
    data[provider] = cfg
    save_all(data)


def set_verify_error(provider: str, error: str) -> None:
    data = load_all()
    cfg = dict(data.get(provider, {}))
    cfg["verified_at"] = ""
    cfg["verify_error"] = error[:500]
    data[provider] = cfg
    save_all(data)


def disconnect(provider: str) -> None:
    """Xoa token nhung GIU app da khai (client_id/secret/page_id_hint)."""
    data = load_all()
    cfg = dict(data.get(provider, {}))
    for f in DISCONNECT_CLEARS[provider]:
        cfg.pop(f, None)
    cfg["updated_at"] = _now()
    data[provider] = cfg
    save_all(data)
