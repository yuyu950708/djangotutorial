# 🍴 等等吃啥（EatWhat）

這是一個「美食分享＋選擇困難救星」的小平台。大家可以發文、看文、用標籤/分類找靈感，還能按讚、留言、收藏。

---

## ✅ 使用者故事（User Story）

> 身為一個面對三餐要吃啥，每次都選擇困難的使用者，我希望可以用「分類/標籤」去找貼文，參考別人的美食分享，讓我更快決定要吃什麼。

---

## 🌱 核心願景（簡單版）

- **現在要做的事**：幫大家解決「午餐/晚餐不知道吃什麼」。
- **未來可以做的事**：如果之後發現大家常吃高熱量外食，可以再加上「熱量分析」或「健康標籤」等功能，讓吃飯更健康。

---

## 📋 系統需求（System Requirements）

### 功能性需求（Functional Requirements）

| 模組 | 用到的功能 | 狀態 |
| :--- | :--- | :---: |
| 會員管理 | 註冊、登入/登出、個人資料與頭像 | ✅ 已完成 |
| 社群貼文 | 發文（含圖片）、看貼文、按讚、留言 | ✅ 已完成 |
| 搜尋篩選 | 關鍵字搜尋、分類/標籤篩選 | ✅ 已完成（可再優化） |
| 互動追蹤 | 收藏貼文、追蹤會員 | ✅ 已完成 |
| 後台管理 | 管理員可管理使用者/貼文/留言/分類/標籤 | ✅ 已完成 |

### 非功能性需求（Non-functional Requirements）

- **資料庫**：MariaDB（關聯式資料庫）
- **安全**：Django 密碼雜湊、CSRF 防護
- **效能**：列表查詢使用 `select_related()` / `prefetch_related()` 等方式減少查詢次數
- **防呆**：搜尋字數、留言長度、重複寫入搜尋紀錄等都有基本處理

---

## 💻 技術棧（Tech Stack）

- **Backend**：Django 5.x（Python）
- **Database**：MariaDB 10.x
- **Frontend**：HTML + Tailwind CSS + Django Template（搭配 Django Form/Widget）
- **DevOps**：Git、HeidiSQL

---

## 🧩 Use Case Diagram（用例圖）

你可以把下面這段 PlantUML 貼到 PlantUML 工具產生圖。

```text
@startuml use_case

title "<color #1A6><size 15>等等吃啥</size></color>\n<color #16A><size 18>Use Case Diagram 用例圖</size></color>\n<color grey>v1.1.0 @2026-03-25</color>\n"

left to right direction

actor "系統管理員" as SysAdmin
actor "非會員" as Guest
actor "一般會員" as Member

package "社群系統功能" {
  usecase UC_Register as "註冊會員" #FCE4EC
  usecase UC_Login as "登入" #FCE4EC

  usecase UC_Logout as "登出" #E1F5FE
  usecase UC_ProfileEdit as "個人資料管理" #E1F5FE
  usecase UC_ProfileView as "查看會員個人頁" #E1F5FE
  usecase UC_Feed as "瀏覽貼文牆" #E1F5FE
  usecase UC_Filter as "依分類 / 標籤篩選貼文" #E1F5FE
  usecase UC_CreatePost as "發布貼文" #E1F5FE
  usecase UC_EditDeletePost as "編輯 / 刪除自己的貼文" #E1F5FE
  usecase UC_Comment as "發表留言" #E1F5FE
  usecase UC_Like as "按讚 / 取消按讚" #E1F5FE
  usecase UC_Collect as "收藏貼文" #E1F5FE
  usecase UC_Follow as "追蹤其他會員" #E1F5FE

  usecase UC_AdminUsers as "後台管理使用者 / 個人資料" #FFF3E0
  usecase UC_AdminContent as "後台管理貼文 / 留言" #FFF3E0
  usecase UC_AdminTaxonomy as "後台管理分類 / 標籤" #FFF3E0
  usecase UC_AdminRole as "使用者角色 / 權限管理" #FFF3E0
}

Guest --> UC_Register
Guest --> UC_Login

Member --> UC_Logout
Member --> UC_ProfileEdit
Member --> UC_ProfileView
Member --> UC_Feed
Member --> UC_Filter
Member --> UC_CreatePost
Member --> UC_Like
Member --> UC_Comment
Member --> UC_Collect
Member --> UC_Follow

SysAdmin --> UC_AdminUsers
SysAdmin --> UC_AdminContent
SysAdmin --> UC_AdminTaxonomy
SysAdmin --> UC_AdminRole

UC_CreatePost ..> UC_EditDeletePost : <<extend>>
UC_Feed ..> UC_Filter : <<extend>>

@enduml
```

---

## 🧱 ERD / DBML（資料表設計）

下面是 DBML（方便用工具畫 ERD）：

```text
Table users {
  id integer [primary key]
  username varchar [unique]
  password varchar
  email varchar [unique]
  role varchar [default: 'member']
  created_at timestamp
}

Table profiles {
  user_id integer [primary key, unique]
  avatar varchar
  bio text
  dietary_preference varchar
}

Table categories {
  id integer [primary key]
  name varchar
}

Table tags {
  id integer [primary key]
  name varchar [unique]
}

Table search_logs {
  id integer [primary key]
  user_id integer
  keyword varchar
  created_at timestamp
}

Table posts {
  id integer [primary key]
  user_id integer
  category_id integer
  title varchar
  content text
  image_url varchar
  like_count integer [default: 0]
  created_at timestamp
  updated_at timestamp
}

Table likes {
  id integer [primary key]
  post_id integer
  user_id integer
  created_at timestamp
}

Table comments {
  id integer [primary key]
  post_id integer
  user_id integer
  content text
  created_at timestamp
}

Table follows {
  id integer [primary key]
  follower_id integer
  following_id integer
  created_at timestamp
}

Table collections {
  id integer [primary key]
  user_id integer
  post_id integer
  created_at timestamp
}

Ref: profiles.user_id - users.id
Ref: posts.user_id > users.id
Ref: posts.category_id > categories.id
Ref: search_logs.user_id > users.id
Ref: comments.post_id > posts.id
Ref: comments.user_id > users.id
Ref: likes.post_id > posts.id
Ref: likes.user_id > users.id
Ref: follows.follower_id > users.id
Ref: follows.following_id > users.id
Ref: collections.user_id > users.id
Ref: collections.post_id > posts.id
```

---

## 🧭 主要頁面（給 demo / Notion 放圖用）

- 貼文牆（首頁）：搜尋、分類/標籤篩選、發文、按讚、留言、收藏
- 單篇貼文：看內容＋互動
- 我的收藏：`/collections/`
- 個人頁：看個人資料與貼文、追蹤/取消追蹤
- 後台管理：`/admin/`

---

## 🚀 開發人員同步指南

### 1. 安裝套件

```powershell
pip install -r requirements.txt
```

### 2. 建立 MariaDB 資料庫

- Database Name：`eat_what`
- Collation：`utf8mb4_unicode_ci`

### 3. 設定資料庫連線

到 `mysite/settings.py` 修改 `DATABASES`（改成你自己的帳密與 port）。

### 4. 建表

```powershell
python manage.py migrate
```

### 5. 建超級管理員

```powershell
python manage.py createsuperuser
```

### 6. 啟動

```powershell
python manage.py runserver
```

