# 🍴 等等吃啥 - 開發人員同步指南

組員你好！目前專案已切換到 **MariaDB** 環境。請在 pull 專案後，依照下面步驟完成本機設定。

## 1. 安裝套件

先進到專案根目錄，安裝 Python 依賴：

```
pip install -r requirements.txt
```

目前專案資料庫驅動使用的是 `PyMySQL`，已包含在 `requirements.txt` 內。

## 2. 準備資料庫

請打開 HeidiSQL 或你習慣的資料庫管理工具，手動建立一個資料庫：

- Database Name：`eat_what`
- Collation：`utf8mb4_unicode_ci`

## 3. 修改本機資料庫連線設定

請開啟 [mysite/settings.py]
找到 `DATABASES` 區塊，依照你的本機 MariaDB 環境修改下面欄位：

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "eat_what",
        "USER": "root", # 帳號
        "PASSWORD": "****", # 密碼
        "HOST": "127.0.0.1",
        "PORT": "3306", # 埠號
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
```


## 4. 同步資料表結構

在終端機執行：

```
python manage.py migrate
```

## 5. 建立超級管理員

如果你本機還沒有管理員帳號，請執行：

```
python manage.py createsuperuser
```

`seed_data` 會把4篇測試貼文作者綁到第一個超級管理員，所以這一步建議先做。

## 6. 灌入測試資料

執行以下指令後，系統會自動建立：

- 3 個分類：`中式`、`日式`、`美式`
- 3 個標籤：`辣`、`健康`、`便宜`
- 10 篇測試貼文

每次執行 `seed_data` 都會先清掉舊的 seed 測試貼文，再重建一批新的，不會越塞越多。

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
- 目前專案已不再使用 SQLite，也不需要 `polls` app
