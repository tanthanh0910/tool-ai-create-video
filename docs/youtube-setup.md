# Ket noi YouTube

Ban tu tao OAuth client cua rieng minh. Vi ban la chu app nen ban tu la test user
cua chinh minh -> dung duoc ngay, khong phai cho Google duyet scope `youtube.upload`
(cho duyet mat vai tuan).

## 1. Tao project + bat API

1. Vao https://console.cloud.google.com/ -> tao project moi (hoac chon project co san).
2. **APIs & Services** -> **Library** -> tim **YouTube Data API v3** -> **Enable**.

## 2. Khai man hinh dong y

**APIs & Services** -> **OAuth consent screen**:

- User type: **External**
- Dien ten app, email ho tro, email lien he
- **Scopes**: them
  - `https://www.googleapis.com/auth/youtube.upload`
  - `https://www.googleapis.com/auth/youtube.readonly`

> Thieu `youtube.readonly` thi tool khong doc duoc `channels.list?mine=true` de lay
> Channel ID + ten kenh -> bao *insufficient permission*.

## 3. Tao OAuth client

**Credentials** -> **Create Credentials** -> **OAuth client ID**:

- Application type: **Web application**
- **Authorized redirect URIs**: dan Y HET chuoi hien trong tool:

```
http://localhost:5000/api/me/channels/youtube/callback
```

Go tay chuoi nay la nguon loi so mot. Google chi bao `redirect_uri_mismatch`
chu khong noi sai o dau. Dung nut **Copy** trong tool.

Bam **Create** -> copy **Client ID** va **Client Secret**.

## 4. Khai vao tool

Tab **📡 Kenh Dang Bai** -> the YouTube -> **⚙ Khai ung dung** -> dan Client ID +
Client Secret -> **Luu** -> **Ket noi**.

## 5. QUAN TRONG: Publish app

App de o che do **Testing** thi Google **thu hoi refresh token sau dung 7 ngay**
-> tool bao `invalid_grant`. Day la thiet ke cua Google, khong phai loi.

Thoat bang: **Google Auth Platform** -> **Audience** -> **Publish app**.
Co hieu luc ngay, khong phai cho duyet (*verification* la chuyen khac, tuy chon).

Publish xong **phai ket noi lai** vi token cu van mang han 7 ngay.

## Han muc

- Quota mac dinh **10.000 don vi/ngay**, moi `videos.insert` ton **1.600**
  -> khoang **6 video/ngay**.
- Audit chi de tang quota, **khong phai** de mo khoa dang cong khai. App chua audit
  van dang video cong khai duoc binh thuong.

## Loi hay gap

| Loi | Nguyen nhan |
|---|---|
| `redirect_uri_mismatch` | Redirect URI ben Google khac chuoi trong tool. Copy lai. |
| `invalid_grant` | App con o che do Testing (token chet sau 7 ngay). Publish app roi ket noi lai. |
| `insufficient permission` | Thieu scope `youtube.readonly`. |
| Khong nhan `refresh_token` | Vao Tai khoan Google > Quyen truy cap cua ben thu ba, go app ra roi ket noi lai. |
| `403 quota` | Het 10.000 don vi hom nay. Doi sang ngay mai. |

> `videos.update` (sua video sau khi dang) can them scope `youtube` hoac
> `youtube.force-ssl`. Chi co `upload` + `readonly` thi tra 403. Tool nay chi dang,
> khong sua, nen khong can.
