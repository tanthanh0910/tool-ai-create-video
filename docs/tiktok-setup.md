# Ket noi TikTok

TikTok khac YouTube/Facebook o **hai diem quan trong**, doc truoc khi lam:

### 1. Phai khai app dang **Desktop**, khong phai Web

Web Login Kit bat `redirect_uri` phai la HTTPS -> `http://localhost:5000` khong dung duoc.
Desktop Login Kit cho phep `http://localhost:<port>` va `http://127.0.0.1:<port>`.

Doi lai Desktop bat buoc **PKCE**, tool da lam san. Luu y ky thuat: TikTok doi
`code_challenge` la SHA256 ma hoa **hex**, khac chuan OAuth (base64url) - dung sai la
bi tu choi.

### 2. Video vao **Drafts**, khong dang thang

Tool dung scope `video.upload`: video duoc day vao **HOP THU (inbox)** cua app TikTok,
ban mo app bam **Dang** la ra cong khai binh thuong.

Ly do khong dung `video.publish` (dang truc tiep): TikTok **ep moi bai cua app chua qua
audit ve che do private**. Dang truc tiep se ra video chi minh ban xem duoc - vo dung.
Che do Drafts thi chinh ban dang nen khong bi han che.

Keo theo: **TikTok khong nhan caption o che do nay**. Tool in caption ra log de ban copy
dan vao app.

---

## 1. Tao app

1. Vao https://developers.tiktok.com/apps -> **Connect an app**
2. Dien thong tin app, cho duyet buoc tao app (thuong nhanh)

## 2. Bat 2 san pham

Trong app, muc **Add products**:

- **Login Kit** -> chon platform **Desktop**
- **Content Posting API** (bat **Direct Post** hay khong deu duoc; tool chi dung Drafts)

## 3. Khai Redirect URI

Trong **Login Kit** -> **Desktop** -> **Redirect URI**, dan Y HET chuoi hien trong tool:

```
http://localhost:5000/api/me/channels/tiktok/callback
```

Dung nut **Copy** trong tool. Go tay la nguon loi so mot.

## 4. Xin scope

Muc **Scopes** cua app, them:

```
user.info.basic
video.upload
```

`user.info.basic` de tool doc ten tai khoan hien tren badge. Thieu no thi khong biet
da ket noi vao tai khoan nao.

## 5. Lay Client Key / Client Secret

Muc **App details** (hoac **Credentials**) -> copy **Client key** va **Client secret**.

## 6. Khai vao tool

Tab **📡 Kenh Dang Bai** -> the TikTok -> **⚙ Khai ung dung** -> dan Client Key +
Client Secret -> **Luu** -> **Ket noi**.

## Cach dang

1. Chon video, tick **🎵 TikTok**, bam **Dang Video**
2. Doi upload xong (log bao `da vao HOP THU app TikTok`)
3. Mo app TikTok tren **dien thoai** -> tab **Hop thu** (icon thong bao) -> bam vao thong bao
4. TikTok mo trinh chinh sua kem video. Bam **📋 Copy caption** trong tool, dan vao, bam **Dang**

> ⚠️ Video **KHONG** nam o muc "Ban nhap" cua TikTok Studio tren web. Tai lieu TikTok ghi ro:
> *"users must click on inbox notifications to continue the editing flow"*. Ban nhap = 0 la binh thuong.

## Han muc & luu y

- `access_token` chi song **24 gio** -> tool khong luu, moi lan dang doi lai tu
  `refresh_token`.
- `refresh_token` song **365 ngay**. TikTok co the luan chuyen no moi lan lam moi,
  tool tu luu ban moi.
- Upload theo khoi: toi thieu 5MB, toi da 64MB moi khoi, khoi cuoi den 128MB,
  toi da 1000 khoi. Video duoi 5MB gui nguyen mot khoi.
- Rate limit: 6 lan mo phien upload / phut / tai khoan.

## Loi hay gap

| Loi | Nguyen nhan |
|---|---|
| `redirect_uri` bi tu choi | Khai app dang Web thay vi Desktop, hoac chuoi khong khop |
| `invalid_client` | Client key / secret sai |
| `invalid_grant` | `refresh_token` het han (qua 365 ngay) -> Ket noi lai |
| `scope_not_authorized` | Chua xin scope `video.upload`, hoac chua bat Content Posting API |
| "Mat code_verifier cua PKCE" | Mo lai lien ket ket noi cu. Bam **Ket noi** lai tu tool |
| Video khong thay trong app | Xem **Hop thu**, khong phai Feed. Draft cho toi 7 ngay |
