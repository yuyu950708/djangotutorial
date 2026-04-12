# 🍴 等等吃啥 (EatWhat)

美食社群平台專案，提供會員註冊登入、貼文分享、留言按讚，以及管理員後台管理等功能。

---

## 📋 系統需求說明 (System Requirements)

本專案旨在建立一個高效、直覺的美食社群平台，以下為系統核心需求規劃：

### 1. 功能性需求 (Functional Requirements)

| 模組 | 功能描述 | 狀態 |
| :--- | :--- | :---: |
| **會員管理** | 提供註冊、登入/登出，以及個人資料與頭像維護。 | ✅ 已完成 |
| **社群貼文** | 支援發布含圖片之貼文，提供按讚與留言互動功能。 | ✅ 已完成 |
| **搜尋篩選** | 具備關鍵字搜尋與分類/標籤篩選功能。 | ✅ 已完成（可優化） |
| **互動追蹤** | 提供貼文收藏與會員間的追蹤功能，強化社群黏性。 | ⏳ 待開發 |
| **後台管理** | 管理員可針對使用者、內容與分類標籤進行 CRUD 維護。 | ✅ 已完成 |

### 2. 非功能性需求 (Non-functional Requirements)

- **資料架構**：採用 **MariaDB** 關聯式資料庫，確保資料存取效能與結構完整性（如 Post 與 Tag 的多對多關聯）。
- **安全性**：全面導入 Django 內建密碼雜湊加密與 **CSRF 防護**。
- **介面整合**：前端整合 CSS Framework（仍在調整 class/相容性），並利用 **Django Form/Widget** 實現 UI 一致性。
- **效能優化**：查詢持續優化（例如 `select_related()` / `prefetch_related()`；必要時 `.distinct()`），確保計數與結果正確。

### 💻 技術棧 (Tech Stack)

- **Backend**: Django 5.x (Python)
- **Database**: MariaDB 10.x
- **Frontend**: HTML5, CSS3, JavaScript, Django Template
- **DevOps**: Git (Fork), HeidiSQL

---

## 🧭 Admin 客製化規劃（已落地）

已完成以下後台客製化：

- 站台標題：`site_header/site_title/index_title`
- 列表體驗：`date_hierarchy`、`ordering`、`list_per_page`、`list_select_related`
- Filter/搜尋：`list_filter`（含 tags/author）、`search_fields`
- Inline：Post 編輯頁可 inline 編輯 Comment
- Actions：批次重算 `like_count`、匯出選取貼文 CSV
- 匯出：整合 `django-import-export`（Post 可匯出）

---

## 🧩 系統設計：URL Router 規劃（Endpoints 對照表）

### Web（目前已實作）

| 類型 | Path | App / Namespace | View | HTTP Methods | 認證 / 權限 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Admin | `/admin/` | Django Admin | Django Admin Site | GET/POST | Staff / Superuser |
| Tools | `/ckeditor/` | `mysite` | CKEditor uploader URLs | GET/POST | 依 CKEditor 設定與 Django 權限 |
| Auth | `/accounts/register/` | `accounts` | FBV `register` | GET/POST | Guest |
| Auth | `/accounts/login/` | `accounts` | CBV `LoginView` | GET/POST | Guest |
| Auth | `/accounts/logout/` | `accounts` | CBV `LogoutView` | GET | Member |
| Profile | `/accounts/profile/edit/` | `accounts` | FBV `profile_edit` | GET/POST | Member |
| Profile | `/accounts/@<username>/` | `accounts` | FBV `profile_detail` | GET | Public（目前開放） |
| Feed | `/` | `posts` | FBV `feed` | GET/POST | Member（`login_required`） |
| Post | `/<pk>/` | `posts` | FBV `post_detail` | GET | ✅ 已完成 |
| Like | `/<pk>/like-toggle/` | `posts` | FBV `like_toggle` | POST（實作上目前允許 GET 也會走） | Member（`login_required`） |
| Comment | `/<pk>/comment/` | `posts` | FBV `comment_create` | POST | Member（`login_required`） |

### Web（已規劃，尚未完成）

| 功能 | 建議 Path | 說明 |
| :--- | :--- | :--- |
| 分類/標籤篩選 | `/?category=<id>&tag=<id>` 或 `/tags/<id>/` | 目前 model 有 `Category/Tag`，但前台尚未做 UI/查詢 |
| 編輯/刪除貼文 | `/<pk>/edit/`、`/<pk>/delete/` | ✅ 已完成（限貼文作者，資料層過濾 `author=request.user`） |
| 收藏貼文 | `/<pk>/collect-toggle/`、`/collections/` | ✅ 已完成（toggle + 收藏列表） |
| 追蹤會員 | `/accounts/@<username>/follow-toggle/` | ✅ 已完成（禁止自追蹤） |
| 搜尋紀錄 |（隱式）| ✅ 已完成（搜尋時寫入 `SearchLog`） |

### RESTful API（期末範圍：建議納入規劃）

| 資源 | 建議 Endpoint | Methods | 權限（建議） |
| :--- | :--- | :--- | :--- |
| Auth | `/api/auth/login` | POST | Public |
| Profile | `/api/users/<id>/profile` | GET/PATCH | Owner 或 Admin |
| Posts | `/api/posts` | GET/POST | GET: Public/Member，POST: Member |
| Post | `/api/posts/<id>` | GET/PATCH/DELETE | Owner 或 Admin |
| Likes | `/api/posts/<id>/likes` | POST/DELETE | Member |
| Comments | `/api/posts/<id>/comments` | GET/POST | GET: Public/Member，POST: Member |
| Tags | `/api/tags` | GET | Public |
| Categories | `/api/categories` | GET | Public |
| Follow | `/api/follows` | POST/DELETE | Member |
| Collections | `/api/collections` | GET/POST/DELETE | Member |
| Search Logs | `/api/search-logs` | GET | Admin（或 Owner） |

---

## 🛠️ 系統開發（待辦清單）

- 建立資料查詢/統計並顯示於前端
- 將文字統計改為圖表呈現
- 優化 templates（RWD）
- 前端加入 messages（目前 base template 已有 messages 區塊，可持續擴充提示訊息）
- 導入 CAPTCHA、客製化登入頁（視需求）
- 依 Use Cases 透過 Generic View 或其他方式建立表單
- 設計可上傳媒體檔案並編輯欄位資訊的表單

---

## 🚀 開發人員同步指南

### 1. 安裝套件

```powershell
pip install -r requirements.txt
```

### 2. 資料庫準備（MariaDB）

請建立資料庫：

- Database Name：`eat_what`
- Collation：`utf8mb4_unicode_ci`

### 3. 修改本地設定（連線到你的 MariaDB）

請調整 `mysite/settings.py` 的 `DATABASES`：

- `NAME`：通常維持 `eat_what`
- `USER` / `PASSWORD`：你的 MariaDB 帳密
- `HOST`：通常 `127.0.0.1`
- `PORT`：通常 `3306`（若你本機另開埠號請自行調整）

### 4. 同步資料表

```powershell
python manage.py migrate
```

### 5. 建立超級管理員

```powershell
python manage.py createsuperuser
```

### 6. 灌入測試資料

會建立 3 個分類、3 個標籤、10 篇測試貼文；每次執行會先清掉舊的 seed 貼文再重建。

```powershell
python manage.py seed_data
```

### 7. 啟動伺服器

```powershell
python manage.py runserver
```
