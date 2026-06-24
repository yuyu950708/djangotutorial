# 匯入 Notion 教學

## 方法一：整份匯入（建議）

1. 打開 Notion，建立新頁面
2. 右上角 `⋯` → **Import** → **Markdown**
3. 選擇 `EatWhat_Notion.md`
4. 匯入後，圖片可能不會自動顯示（Notion 不讀本機路徑）
5. 在對應標題下方，手動 **拖放** `images/` 資料夾內的 PNG：
   - `use_case.png`
   - `erd.png`
   - `architecture.png`
   - `health_flow.png`
   - `recommendation_flow.png`

## 方法二：複製貼上

1. 用 VS Code 或 Typora 開啟 `EatWhat_Notion.md` 預覽
2. 分段複製到 Notion 頁面
3. 在每個圖表標題下按 `/image` 上傳對應 PNG

## 方法三：只放圖表

若只要圖表頁面：

1. 新建 Notion 頁面「EatWhat 圖表」
2. 依序上傳 5 張 PNG
3. 每張圖下方貼一行說明（見 `EatWhat_Notion.md`）

## 畫面截圖（網站實際畫面）

圖表 PNG 已自動產生；**網站操作截圖**需在本機自行拍攝：

- 參考 `docs/SUBMISSION.md` 截圖清單
- 建議檔名：`screenshot_01_首頁.png`、`screenshot_02_登入.png` …
- 拍完拖入 Notion「畫面截圖區」對應 checkbox 下方

## 重新產生圖表

```bash
cd docs/diagrams
npx -y @mermaid-js/mermaid-cli -i use_case.mmd -o ../notion/images/use_case.png -w 3200 -H 2400 -b white
npx -y @mermaid-js/mermaid-cli -i erd.mmd -o ../notion/images/erd.png -w 3600 -H 3000 -b white
npx -y @mermaid-js/mermaid-cli -i architecture.mmd -o ../notion/images/architecture.png -w 2000 -H 800 -b white
npx -y @mermaid-js/mermaid-cli -i health_flow.mmd -o ../notion/images/health_flow.png -w 2200 -H 1200 -b white
npx -y @mermaid-js/mermaid-cli -i recommendation_flow.mmd -o ../notion/images/recommendation_flow.png -w 2000 -H 1400 -b white
```
