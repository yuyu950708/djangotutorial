# 🍴 等等吃啥 (EatWhat)
「身為一個午餐選擇困難的使用者，我希望透過標籤篩選貼文，參考他人的美食分享，以解決選擇困難並獲取用餐靈感。」

本專案是一個以美食為核心的社群平台，旨在透過直覺的分類與標籤系統，串聯會員間的飲食經驗。

## 📋 系統需求說明 (System Requirements)
本專案旨在建立一個高效、直覺的美食社群平台，以下為系統核心需求規劃：

### 1. 功能性需求 (Functional Requirements)
| 模組 | 功能描述 | 狀態 |
| :--- | :--- | :---: |
| **會員管理** | 提供註冊、登入/登出，以及個人資料與頭像維護。 | ✅ 已完成 |
| **社群貼文** | 支援發布含圖片之食譜貼文，提供按讚與留言互動功能。 | ✅ 已完成 |
| **搜尋篩選** | 具備關鍵字搜尋與分類/標籤篩選功能，搜尋結果具唯一性。 | 🔄 優化中 |
| **互動追蹤** | 提供貼文收藏與會員間的追蹤功能，強化社群黏性。 | ⏳ 待開發 |
| **後台管理** | 管理員可針對使用者、內容與分類標籤進行 CRUD 維護。 | ✅ 已完成 |

### 2. 非功能性需求 (Non-functional Requirements)
- **資料架構**：採用 **MariaDB** 關聯式資料庫，確保資料存取效能與結構完整性。
- **安全性**：導入 Django 內建密碼雜湊與 **CSRF 防護**。
- **介面整合**：前端目前以 Django Template 搭配 Form / Widget 整合頁面，後續持續優化 UI 一致性。
- **效能優化**：搜尋與資料關聯查詢將持續調整，以提升查詢效率與結果正確性。

### 💻 技術棧 (Tech Stack)
- **Backend**: Django 5.x (Python)
- **Database**: MariaDB 10.x
- **Frontend**: HTML5, CSS3, JavaScript, Django Template
- **DevOps**: Git (Fork), HeidiSQL

---

## 🚀 開發人員同步指南


## 1. 安裝套件

先進到專案根目錄，安裝 Python 依賴：

```powershell
pip install -r requirements.txt
```

目前專案資料庫驅動使用的是 `PyMySQL`，已包含在 `requirements.txt` 內。

## 2. 準備資料庫

請打開 HeidiSQL 或你習慣的資料庫管理工具，手動建立一個資料庫：

- Database Name：`eat_what`
- Collation：`utf8mb4_unicode_ci`

## 3. 修改本機資料庫連線設定

請開啟 [mysite/settings.py](C:\Users\11146076\Desktop\djangotutorial\mysite\settings.py)，找到 `DATABASES` 區塊，依照你的本機 MariaDB 環境修改下面欄位：

- `NAME`：通常維持 `eat_what`
- `USER`：你的 MariaDB 帳號，常見是 `root`
- `PASSWORD`：你的 MariaDB 密碼
- `HOST`：通常是 `127.0.0.1`
- `PORT`：預設通常是 `3306`，如果你的本機是另外開的埠號，也請改成自己的值

目前專案中的 `DATABASES` 範例：

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "eat_what",
        "USER": "root",
        "PASSWORD": "root",
        "HOST": "127.0.0.1",
        "PORT": "3308",
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
```

請改成你自己的本機設定，不要直接沿用別人的帳密。

## 4. 同步資料表結構

在終端機執行：

```powershell
python manage.py migrate
```

## 5. 建立超級管理員

如果你本機還沒有管理員帳號，請執行：

```powershell
python manage.py createsuperuser
```

`seed_data` 會把測試貼文作者綁到第一個超級管理員，所以建議先完成這一步。

## 6. 灌入測試資料

執行以下指令後，系統會自動建立：

- 3 個分類：`中式`、`日式`、`美式`
- 3 個標籤：`辣`、`健康`、`便宜`
- 4 篇測試貼文

每次執行 `seed_data` 都會先刪掉舊的 seed 測試貼文，再重建一批新的，不會越塞越多。

```powershell
python manage.py seed_data
```

## 7. 啟動開發伺服器

```powershell
python manage.py runserver
```

打開瀏覽器後可使用：

- 前台首頁：http://127.0.0.1:8000/
- Django Admin：http://127.0.0.1:8000/admin/

## 補充提醒

- 如果 `migrate` 時出現 MariaDB 帳密錯誤，請先檢查 `settings.py` 的 `USER`、`PASSWORD`、`PORT` 是否正確。
- 如果你是第一次開發這個專案，建議順序是：`migrate` -> `createsuperuser` -> `seed_data` -> `runserver`
- 目前專案已不再使用 SQLite，也不需要 `polls` app。
