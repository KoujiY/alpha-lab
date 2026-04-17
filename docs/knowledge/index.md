# alpha-lab 知識庫

這份知識庫服務於**修改 alpha-lab 的 Claude**（不是幫使用者分析投資的 Claude）。目的是讓後續改動這個專案的 Claude 能快速載入相關脈絡，理解目前系統的實作、為什麼這樣設計、修改時的注意事項。

## 定位

- **讀者**：開發者立場的 Claude（或人類開發者）
- **不是**：投資領域的學習筆記（那種內容屬於 `data/reports/` 或另外規劃）
- **不是**：使用者說明（那種內容屬於 `docs/USER_GUIDE.md`）

## 資料夾結構

```
docs/knowledge/
├── index.md                 # 本檔（總覽 + 維護規範）
├── features/                # 五大功能模組（A~E）+ 輔助頁
│   ├── data-panel/          # A：個股數據面板（/stocks/:symbol）
│   ├── screener/            # B：選股篩選器
│   ├── portfolio/           # C：組合推薦
│   ├── tracking/            # D：組合追蹤
│   ├── education/           # E：嵌入式教學
│   ├── reports/             # 分析回顧（/reports）
│   ├── stocks/              # 股票瀏覽列表（/stocks，Phase 8）
│   └── settings.md          # 偏好管理頁（/settings，Phase 8）
├── domain/                  # 投資領域邏輯（系統內部怎麼實作）
├── architecture/            # 系統架構（data models、API、資料流）
├── collectors/              # 數據抓取模組（Phase 1 起細化）
└── ai-integration/          # Claude Code 分析 SOP、Claude API 預留
```

Phase 0 只建資料夾與各自 `README.md`。實際內容**隨 Phase 逐步補寫**。

## 原子化原則

1. **單一概念單一檔案**：每個 `.md` 只講一件事，避免大雜燴。
2. **檔案大小**：約 50~200 行。超過 200 行考慮拆分。
3. **固定 frontmatter**：

   ```markdown
   ---
   domain: features/portfolio   # 對應資料夾路徑
   updated: 2026-04-14
   related: [factors.md, scoring.md]
   ---

   # 概念名稱

   ## 目的
   ## 現行實作
   ## 關鍵檔案
   - [src/alpha_lab/analysis/factors.py](...)
   ## 修改時注意事項
   ```

4. **跨參考**：`related` 欄位列出同知識庫內相關檔案，讓 Claude 能順著讀下去。

## 維護規範（MANDATORY）

以下情況**必須**同步更新對應的知識庫：

1. **新增功能** → 在相關 domain 建立或更新 md
2. **修改現有邏輯**（資料結構、流程、規則） → 更新對應 md 的「現行實作」
3. **重構後介面改變** → 更新「關鍵檔案」路徑 / 函數名稱
4. **刪除功能** → 移除或標記過時的條目

每次 commit 前的同步檢查必須檢查「知識庫是否需更新」。違反會讓知識庫與 codebase 脫節、失去存在意義。

## 修改現有功能前的縱向分析（MANDATORY）

修改任何既有功能前，必須完成縱向分析：

1. **向上（呼叫端）**：grep 所有 import / 呼叫點
2. **向下（依賴鏈）**：沿呼叫鏈讀完關鍵節點
3. **對照知識庫**：確認此功能的對應 `docs/knowledge/` 條目是否與現行 codebase 一致；若不一致，先修知識庫

**常見陷阱**：FastAPI route 或 React page 不需 import 即可存在於導航中，靜態分析無法偵測「已無入口但知識庫仍記載」的殘留，必須人工確認。
