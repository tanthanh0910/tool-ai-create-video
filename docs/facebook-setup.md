# Ket noi Facebook

Dang video len **Trang (Page)**, khong phai trang ca nhan. Ban phai la quan tri vien
cua Trang do.

## 1. Tao app

1. Vao https://developers.facebook.com/apps/ -> **Create App**.
2. Use case: chon **Other** -> loai app: **Business**.
3. Vao app -> **Add Product** -> **Facebook Login** -> **Web**.

## 2. Khai Redirect URI

**Facebook Login** -> **Settings** -> **Valid OAuth Redirect URIs**: dan Y HET chuoi
hien trong tool:

```
http://localhost:5000/api/me/channels/facebook/callback
```

Meta chi bao `redirect_uri_mismatch` chu khong noi sai o dau. Dung nut **Copy**.

## 3. Lay App ID / App Secret

**App settings** -> **Basic** -> copy **App ID** va **App Secret**.

## 4. Quyen can co

App phai xin duoc 3 quyen:

```
pages_show_list
pages_read_engagement
pages_manage_posts
```

O che do **Development**, tai khoan quan tri app dung duoc ngay ma khong can App Review.

## 5. Khai vao tool

Tab **📡 Kenh Dang Bai** -> the Facebook -> **⚙ Khai ung dung** -> dan App ID +
App Secret -> **Luu** -> **Ket noi**.

Tool tu lam ba buoc trong mot cu bam:

```
code -> user token ngan han -> token dai han (60 ngay) -> Page token (khong han)
```

## 6. Page ID goi y — khi nao phai dien

Dien **Page ID goi y** neu roi vao mot trong hai truong hop:

**a) Ban quan tri nhieu Trang.** Tool se bao loi va liet ke ten + ID tung Trang -
no khong tu chon bua, vi chon nham nghia la video len sai Trang ma khong co dau hieu gi.

**b) Trang thuoc Business Portfolio.** `me/accounts` la lenh liet ke va **hay tra rong**
voi loai Trang nay, ke ca khi ban da tick dung Trang luc cap quyen va quyen da duoc
granted day du. Go app khoi Business Integrations cung khong sua duoc. Duong tin cay
duy nhat la biet truoc Page ID roi hoi thang.

**Lay Page ID o dau:** vao Trang -> **Gioi thieu** -> **Trang minh bach**, hoac
https://business.facebook.com/settings/pages.

## Han muc & luu y

- **Toi da 1 GB moi lan dang.** Lon hon can resumable upload, tool chua ho tro
  (se chan som kem thong bao ro).
- Bai dang qua `/{page_id}/videos` **da la cong khai san** (`privacy: EVERYONE`) —
  khong co lua chon rieng tu nhu YouTube.
- Facebook **khong co truong tag** cho video, va video doc bi xep thanh **Reel** khien
  tieu de khong len feed. Vi vay tool gop **tieu de + mo ta + hashtag vao mot caption**.
- Page token co `expires_at: 0` (khong han) nhung `data_access_expires_at` khoang
  **90 ngay** — sau moc do phai ket noi lai.

## Loi hay gap

| Loi | Nguyen nhan |
|---|---|
| `redirect_uri_mismatch` | Redirect URI ben Meta khac chuoi trong tool. |
| "Facebook khong liet ke Trang nao" | Trang thuoc Business Portfolio. Dien Page ID goi y. |
| "Ban quan tri N Trang" | Dien Page ID goi y de chon dung Trang. |
| "Page token khong dung duoc" | Token het han (~90 ngay) hoac bi thu hoi. Ket noi lai. |
