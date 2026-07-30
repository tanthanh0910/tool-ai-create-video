Kết nối YouTube / Facebook để đăng video — bản tóm tắt kiến trúc
1. Mô hình quyền: mỗi user tự khai app của mình
Không dùng một app chung của hệ thống. Mỗi user tự tạo OAuth client ở Google Cloud / app ở Meta, dán client_id + client_secret vào, rồi bấm Kết nối.

Lý do: user là chủ app nên tự là test user của chính mình → dùng được ngay, không phải chờ Google duyệt scope youtube.upload (mất vài tuần). App chung thì mọi user đều kẹt chờ duyệt.

Có đường lùi về app hệ thống (YOUTUBE_CLIENT_ID/FACEBOOK_APP_ID trong env) khi user chưa khai gì — nhưng khai dở dang (có ID, mất secret) thì trả None chứ không lùi, vì chạy OAuth dưới client user chưa đăng ký chỉ ra redirect_uri_mismatch ở phía Google/Meta, lỗi đó không chỉ ngược về được.

2. Lưu trữ
Một cột JSONB users.social_channels:


{
  "youtube": {
    "client_id": "...",           // công khai
    "client_secret": "<Fernet>",  // mã hoá
    "refresh_token": "<Fernet>",  // mã hoá
    "channel_id": "UC...",        // đích đăng, chỉ OAuth ghi
    "channel_title": "...",
    "verified_at": "...", "verify_error": "", "verified_name": "...",
    "updated_at": "..."
  },
  "facebook": {
    "app_id": "...", "app_secret": "<Fernet>",
    "page_access_token": "<Fernet>",
    "page_id": "...",             // ĐÍCH ĐĂNG, chỉ OAuth ghi
    "page_id_hint": "...",        // user tự gõ, CHỈ để chọn Trang lúc kết nối
    "page_name": "...",
    /* + cụm verify như trên */
  }
}
Mã hoá Fernet bằng khoá dẫn xuất từ JWT_SECRET (đổi JWT_SECRET = mọi token phải nhập lại).

Ba quy ước bắt buộc giữ:

to_public() trả ra API chỉ có trường công khai + cờ <tên>_set; không bao giờ trả bí mật. credentials() giải mã, chỉ gọi ở tầng worker.
PATCH bí mật: vắng mặt/null = giữ nguyên, "" = xoá, có giá trị = thay mới.
Gán lại cả dict (user.social_channels = merged) vì SQLAlchemy không track thay đổi bên trong JSONB.
Tách hai mức trạng thái, không gộp: configured = đã điền đủ ô (chuỗi rác vẫn tính); verified_at = đã gọi thật API và thành công tại đúng mốc đó. UI luôn hiện kèm giờ, không dùng dấu tích vĩnh viễn — token có thể bị thu hồi bất cứ lúc nào.

Chỉ xoá trạng thái verify khi đổi trường invalidating: YouTube là channel_id/client_id/client_secret/refresh_token; Facebook chỉ page_id/page_access_token (Page token tự mang danh tính app bên trong, đổi app_id/app_secret không làm nó hỏng — xoá verify sẽ là báo động sai).

3. Luồng OAuth

FE bấm Kết nối
  → GET /api/me/channels/{provider}/connect     (có Authorization)
     trả về { url } — FE tự chuyển trình duyệt sang
  → user đăng nhập, chọn kênh/Trang, cấp quyền
  → nền tảng gọi GET /api/me/channels/{provider}/callback?code=&state=
     đổi code lấy token → lưu → verify ngay → redirect về /settings/channels?status=&msg=
state là JWT chứa {sub: user_id, p: provider, exp: +10 phút}, ký bằng jwt_secret. Bắt buộc, vì callback do trình duyệt gọi nên không mang được header Authorization — danh tính phải đi kèm trong state. Đọc ra phải kiểm cả provider khớp.

Redirect URI = f"{OAUTH_REDIRECT_BASE}/api/me/channels/{provider}/callback". Khai y hệt ở console hai bên. Local trỏ vào cổng Vite (5174) chứ không phải uvicorn (8077): trình duyệt bị đá về đây, Vite proxy /api sang API; đi thẳng 8077 thì callback chạy nhưng redirect về UI rơi vào trang trống.

Kết nối lại phải trúng đúng kênh cũ. So channel_id/page_id mới với cũ, lệch thì từ chối kèm tên kênh cũ. Không chặn thì user đang đăng nhập tài khoản khác sẽ âm thầm thay kênh: badge vẫn xanh, video sau đó lên sai chỗ — loại lỗi chỉ phát hiện khi đã đăng nhầm. Muốn đổi thật thì bấm Ngắt trước.

Ngắt kết nối xoá token nhưng GIỮ app đã khai (client_id/secret/page_id_hint). Xoá sạch thì mỗi lần Ngắt user phải đi lấy lại Client ID ở Google Cloud.

4. Khác biệt hai nền tảng
YouTube

Scope: youtube.upload và youtube.readonly. Thiếu readonly thì không đọc được channels.list?mine=true để lấy Channel ID + tên kênh → báo insufficient permission.
Xin quyền phải có access_type=offline + prompt=consent, không thì Google không trả refresh_token.
Mỗi lần đăng: đổi refresh_token → access_token rồi mới upload.
App ở chế độ Testing thì Google thu hồi refresh token sau đúng 7 ngày → invalid_grant. Thoát bằng Google Auth Platform → Audience → Publish app (có hiệu lực ngay, không phải chờ duyệt; verification là chuyện khác, tuỳ chọn). Publish xong phải kết nối lại vì token cũ vẫn mang hạn 7 ngày.
Facebook — đổi token ba bước, làm hết trong một cú bấm:


code → user token ngắn hạn → token dài hạn (60 ngày) → Page token (không hạn)
Scope: pages_show_list,pages_read_engagement,pages_manage_posts.
Page token có expires_at: 0 nhưng data_access_expires_at ~90 ngày.
Không có trường tag cho video; video dọc bị xếp thành Reel và title không lên feed → phải gộp title + description + hashtag vào một chuỗi caption.
5. Chọn Trang Facebook — 4 nhánh, theo đúng thứ tự

1. có hint & hint nằm trong me/accounts  → lấy Trang đó
2. có hint & không nằm (kể cả list rỗng) → GET /{hint}?fields=access_token
                                            thất bại → lỗi rõ ràng
3. không hint & me/accounts trả NHIỀU    → LỖI, liệt kê tên + ID từng Trang
4. không hint & đúng 1 Trang             → lấy Trang đó
   không hint & rỗng                     → LỖI "không liệt kê Trang nào"
Nhánh 2 là bắt buộc: me/accounts là lệnh liệt kê và hay trả rỗng với Trang thuộc Business Portfolio, kể cả khi user đã tick chọn đúng Trang và quyền đủ granted. Đường tin cậy duy nhất là biết trước Page ID rồi hỏi thẳng.

Nhánh 3 tuyệt đối không được lấy bừa pages[0] — user quản trị nhiều Trang sẽ đăng nhầm mà không có dấu hiệu nào.

page_id_hint phải là trường RIÊNG, tách khỏi page_id. Hint là thứ user gõ; page_id là đích đăng bài và chỉ OAuth ghi được. Gộp chung thì gõ nhầm một chữ số là đổi đích đăng mà configured vẫn xanh.

6. Đăng bài
Chạy sau khi render xong, trong worker của queue video. Kết quả từng kênh ghi vào params["publish"], bóc ra qua property RenderJob.publish để không đẩy params thô ra API.

Token hết hạn thì job vẫn done và file vẫn tải về được — đăng hỏng không được kéo cả lượt xuất theo.

YouTube — resumable upload:


POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status
→ lấy Location, PUT stream theo khối 8MB (đọc bằng asyncio.to_thread, không nạp cả file vào RAM)
status.privacyStatus nhận public | unlisted | private, mặc định private. App chưa audit vẫn đăng công khai được — audit chỉ để tăng quota, không phải để mở khoá công khai. Quota mặc định 10.000 đơn vị/ngày, mỗi videos.insert tốn 1.600 → ~6 video/ngày.

Facebook: POST /{page_id}/videos với description = caption đã gộp. Giới hạn 1GB mỗi lần đăng (lớn hơn cần resumable, chưa hỗ trợ → chặn sớm kèm thông báo rõ).

Hashtag: tối đa 10 (_MAX_HASHTAGS). Con số đến từ YouTube — quá 15 hashtag thì YouTube bỏ qua toàn bộ hashtag của video, nên chừa biên. YouTube có cả snippet.tags (người xem không thấy, chỉ để tìm kiếm) lẫn hashtag trong mô tả; hai thứ khác nhau, UI phải nói rõ.

7. API

GET    /api/me/channels                      cấu hình của mình (đã lọc bí mật)
GET    /api/me/channels/available            {ready, redirect_uri} mỗi nền tảng
PUT    /api/me/channels/{provider}/app       lưu client_id/secret (+ page_id_hint)
GET    /api/me/channels/{provider}/connect   → { url } để chuyển trình duyệt
GET    /api/me/channels/{provider}/callback  ← nền tảng gọi về, redirect ra UI
DELETE /api/me/channels/{provider}           ngắt (giữ app)
POST   /api/projects/{pid}/publish-meta/suggest   AI viết title/description/tags
Mọi user đều vào được (kênh của họ thì họ tự setup) — không để trong khu Quản trị chỉ admin vào được.

8. Frontend
Trang /settings/channels — mỗi nền tảng một thẻ: badge 4 mức (Chưa khai ứng dụng / Chưa kết nối / Cần kết nối lại + nguyên văn lỗi / Đã kết nối + mốc giờ), nút Kết nối (khoá khi chưa khai app) + Ngắt, form khai app gập lại được, và panel hướng dẫn trượt từ mép phải.

Form khai app hiện Redirect URI thật kèm nút copy — gõ tay chuỗi này là nguồn lỗi số một, mà cả hai nền tảng chỉ báo redirect_uri_mismatch chứ không nói sai ở đâu.

Modal Xuất — mục Chia sẻ: chọn kênh, chế độ hiển thị YouTube (Công khai / Không công khai / Riêng tư), 3 ô nội dung (title, description, tags — không thêm ô keyword thứ tư), nút AI viết từ phụ đề, và xem trước dựng theo bố cục thật của từng nền tảng.

Nội dung riêng cho từng kênh: mặc định dùng chung, tách khi cần. Bản riêng chỉ sinh ra khi gõ ký tự đầu tiên, không phải khi mở tab — tạo sớm hơn thì một bản riêng rỗng sẽ âm thầm che mất nội dung chung. Tab của kênh vừa bị bỏ tick phải tự quay về "Dùng chung", nếu không user gõ vào bản riêng của kênh không đăng và nội dung đó bị lọc bỏ lúc xuất.

9. Cấu hình

OAUTH_REDIRECT_BASE=http://localhost:5174     # local: cổng Vite
# production: https://<tên miền công khai>, không cổng, không dấu / cuối
Đây là biến duy nhất bắt buộc. YOUTUBE_CLIENT_ID/SECRET, FACEBOOK_APP_ID/SECRET chỉ là app hệ thống dự phòng, để trống cũng chạy.

10. Danh sách bẫy đã gặp thật
Backend

Hàm đọc file theo khối để stream phải là async def — def thường sẽ ném RuntimeError: Attempted to send an sync request with an AsyncClient instance, và lỗi chỉ nổ lúc đăng thật.
arq không hot-reload. Sửa code xong không restart worker = chạy code cũ, không lỗi không log. Đây là lý do nút chọn chế độ hiển thị "không có tác dụng" dù code đã đúng.
render_video chạy ở queue riêng (rovoice:video) → phải chạy thêm một tiến trình worker nữa, không thì job kẹt "Trong hàng đợi" vĩnh viễn.
--reload của uvicorn chỉ theo dõi file .py, không nạp lại biến môi trường. Sửa .env xong phải tắt hẳn rồi chạy lại.
pydantic-settings đọc theo thứ tự: biến môi trường → file env_file → giá trị mặc định trong code. Mặc định trong code chỉ là đường lùi cuối cùng.
Facebook

me/accounts trả rỗng với Trang thuộc Business Portfolio — không phải do thiếu quyền, và gỡ app khỏi Business Integrations không sửa được.
Bài đăng qua /{page_id}/videos đã là công khai sẵn (privacy: EVERYONE).
YouTube

videos.update cần scope youtube hoặc youtube.force-ssl; chỉ có upload + readonly thì trả 403 insufficientPermissions. Muốn sửa video sau khi đăng phải xin thêm scope.
Refresh token chết sau 7 ngày khi app ở Testing — thiết kế của Google, không phải lỗi.
Bảo mật khi debug

Log callback phải che code=, state=, token và secret. Nhận log từ user thì kiểm trước khi dùng lại giá trị nào.
11. Bản đồ file

app/services/oauth_connect.py     make_state/read_state, authorize_url, exchange, redirect_uri
app/services/social_channels.py   to_public/credentials/merge/app_credentials/disconnect
app/services/social_verify.py     gọi thật API rồi ghi verified_at / verify_error
app/services/social_publish.py    upload YouTube resumable + Facebook Graph, hashtag, caption
app/services/publish_meta.py      AI viết title/description/tags từ phụ đề (+ khung hình)
app/routers/channels.py           7 endpoint ở mục 7
app/queue/tasks.py                _publish_render, _publish_content (bản riêng/dùng chung)
web/src/pages/ChannelsPage.tsx    trang Kênh đăng bài
web/src/components/channels/SetupGuide.tsx   panel hướng dẫn
web/src/components/editor/ExportModal.tsx    mục Chia sẻ trong modal Xuất
docs/youtube-setup.md, docs/facebook-setup.md