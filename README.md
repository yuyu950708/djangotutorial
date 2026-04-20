# 🍴 等等吃啥（EatWhat）

這是一個「美食分享＋選擇困難救星」的小平台。大家可以發文、看文、用標籤/分類找靈感，還能按讚、留言、收藏。

---

## 使用者故事（User Story）

> 身為一個面對三餐要吃啥，每次都選擇困難的使用者，我希望可以用「分類/標籤」去找貼文，參考別人的美食分享，讓我更快決定要吃什麼。

---

## 核心願景

- **現在要做的事**：幫大家解決「午餐/晚餐不知道吃什麼」。
- **未來可以做的事**：如果之後發現大家常吃高熱量外食，可以再加上「熱量分析」或「健康標籤」等功能，讓吃飯更健康。

---

## 系統需求（System Requirements）

### 功能性需求（Functional Requirements）

| 模組 | 用到的功能 | 狀態 |
| :--- | :--- | :---: |
| 會員管理 | 註冊、登入/登出、個人資料與頭像 |
| 社群貼文 | 發文（最多 3 張附圖）、看貼文、按讚、巢狀留言 | 
| 搜尋篩選 | 關鍵字搜尋、分類/標籤篩選 | 
| 互動追蹤 | 收藏貼文、追蹤會員、留言按讚 |
| 後台管理 | 管理員可管理使用者/貼文/留言/分類/標籤 |

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

## ERD / DBML（資料表設計）

DBML：

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
  image2 varchar
  image3 varchar
  visibility varchar [default: 'public', note: 'public/private']
  like_count integer [default: 0]
  created_at timestamp
  updated_at timestamp
}

Table posts_tags {
  id integer [primary key]
  post_id integer
  tag_id integer
}

Table likes {
  id integer [primary key]
  post_id integer
  user_id integer
  created_at timestamp
}

Table post_comment {
  id integer [primary key]
  post_id integer
  user_id integer
  parent_id integer [null]
  root_id integer [null]
  content text
  like_count integer [default: 0]
  created_at timestamp
  updated_at timestamp
  is_locked boolean [default: false]
  is_pinned boolean [default: false]
}

Table post_comment_likes {
  id integer [primary key]
  user_id integer
  comment_id integer
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

Table ai_chat_logs {
  id integer [primary key]
  user_id integer
  message text
  image varchar [null]
  assistant_reply text
  model_name varchar
  created_at timestamp
}

Ref: profiles.user_id - users.id
Ref: posts.user_id > users.id
Ref: posts.category_id > categories.id
Ref: posts_tags.post_id > posts.id
Ref: posts_tags.tag_id > tags.id
Ref: search_logs.user_id > users.id
Ref: post_comment.post_id > posts.id
Ref: post_comment.user_id > users.id
Ref: post_comment.parent_id > post_comment.id
Ref: post_comment.root_id > post_comment.id
Ref: post_comment_likes.user_id > users.id
Ref: post_comment_likes.comment_id > post_comment.id
Ref: likes.post_id > posts.id
Ref: likes.user_id > users.id
Ref: follows.follower_id > users.id
Ref: follows.following_id > users.id
Ref: collections.user_id > users.id
Ref: collections.post_id > posts.id
Ref: ai_chat_logs.user_id > users.id
```

## 用例圖（Use Case）

以下為 **PlantUML**（與實作一致：訪客可瀏覽「公開」貼文並篩選／搜尋；互動與 AI 需登入）。若 GitHub 預覽無法渲染，可用 [PlantUML Live](https://www.plantuml.com/plantuml/uml/) 或 VS Code PlantUML 外掛貼上繪製。

```plantuml
@startuml use_case

title "<color #1A6><size 15>等等吃啥</size></color>\n<color #16A><size 18>Use Case Diagram 用例圖</size></color>\n<color grey>v1.2.0 @2026-04-20</color>\n"

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
    usecase UC_Feed as "瀏覽貼文牆\n（訪客僅公開貼文）" #E1F5FE

    usecase UC_Filter as "依分類 / 標籤篩選貼文" #E1F5FE
    usecase UC_Search as "關鍵字搜尋貼文" #E1F5FE

    usecase UC_CreatePost as "發布貼文" #E1F5FE
    usecase UC_EditDeletePost as "編輯 / 刪除自己的貼文" #E1F5FE
    usecase UC_Visibility as "設定貼文可見性\n（公開 / 僅自己）" #E1F5FE

    usecase UC_Comment as "發表 / 回覆留言" #E1F5FE
    usecase UC_CommentLike as "留言按讚 / 取消" #E1F5FE
    usecase UC_Like as "貼文按讚 / 取消" #E1F5FE
    usecase UC_Collect as "收藏貼文" #E1F5FE
    usecase UC_Follow as "追蹤其他會員" #E1F5FE

    usecase UC_AI as "使用 AI 美食助理" #E1F5FE

    usecase UC_AdminUsers as "後台管理使用者 / 個人資料" #FFF3E0
    usecase UC_AdminContent as "後台管理貼文 / 留言" #FFF3E0
    usecase UC_AdminTaxonomy as "後台管理分類 / 標籤" #FFF3E0
    usecase UC_AdminRole as "使用者角色 / 權限管理" #FFF3E0
}

Guest --> UC_Register
Guest --> UC_Login
Guest --> UC_Feed
Guest --> UC_Filter
Guest --> UC_Search

Member --> UC_Logout
Member --> UC_ProfileEdit
Member --> UC_ProfileView
Member --> UC_Feed
Member --> UC_Filter
Member --> UC_Search
Member --> UC_CreatePost
Member --> UC_EditDeletePost
Member --> UC_Like
Member --> UC_Comment
Member --> UC_CommentLike
Member --> UC_Collect
Member --> UC_Follow
Member --> UC_AI

SysAdmin --> UC_AdminUsers
SysAdmin --> UC_AdminContent
SysAdmin --> UC_AdminTaxonomy
SysAdmin --> UC_AdminRole

' UML：選擇性擴充行為由「擴充用例」指向「基礎用例」（篩選／搜尋皆可視為在瀏覽貼文牆上的延伸）
UC_Feed <|.. UC_Filter : <<extend>>
UC_Feed <|.. UC_Search : <<extend>>

' 發布與編輯流程內含「可見性」設定（表單欄位），勿用「發布 extend 編輯刪除」易誤解生命週期
UC_CreatePost ..> UC_Visibility : <<include>>
UC_EditDeletePost ..> UC_Visibility : <<include>>

note bottom of UC_AI
須登入。後端寫入 ai_chat_logs
（提問、回覆、模型名稱等）
end note

@enduml
```

## 🚀 開發人員同步指南

### 1. 安裝套件

```powershell
pip install -r requirements.txt
```

### 2. 建立 MariaDB 資料庫

- Database Name：`eat_what`
- Collation：`utf8mb4_unicode_ci`

### 3. 設定資料庫連線

到 `mysite/settings.py` 修改 `DATABASES`（改成自己的帳密與 port）。

### 4. 建表

```powershell
python manage.py migrate
```

### 5. 建superuser

```powershell
python manage.py createsuperuser
```

### 6. 啟動

```powershell
python manage.py runserver
```

