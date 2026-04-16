---
domain: features/education/l2-panel
updated: 2026-04-17
related: [tooltip.md, reasons.md]
---

# L2 詳解面板

## 目的

spec §10「兩層教學」裡的 L2：使用者在 Tooltip 看完 L1 簡短定義後，點「看完整說明 →」會打開右側 slide-in panel，顯示對應術語 / 主題的完整 markdown。

## 現行實作（Phase 4）

### 內容載體

L2 內容以 **markdown 檔**儲存於 `backend/src/alpha_lab/education/l2/<id>.md`，採 YAML frontmatter：

```markdown
---
id: PE
title: 本益比（PE）深度解說
related_terms: [EPS, PB, ROE]
---

# 正文標題

自由 markdown...
```

- `id`：唯一識別（通常對應 glossary key，或主題短代號）
- `title`：顯示於 L2 Panel 標題列
- `related_terms`：相關術語的 key，前端可延伸做跳轉（Phase 4 先不做）

### Loader

`education/loader.py`：
- 掃 `education/l2/*.md`、`_split_frontmatter` 解析 YAML + body
- `@lru_cache` 單例快取（個人工具，不需 hot reload）
- `load_l2_topics(path?) -> dict[id, L2Topic]`、`get_l2_topic(id) -> L2Topic | None`
- `clear_cache()` 給測試用

### 初版 5 個 topic

- `PE` — 本益比深度
- `ROE` — ROE 與杜邦分析
- `dividend-yield` — 殖利率與配息穩定
- `monthly-revenue` — 月營收 / YoY / MoM
- `multi-factor-scoring` — 本系統四因子怎麼運作

### API（Task 4 待補）

- `GET /api/education/l2`：list meta
- `GET /api/education/l2/{id}`：full payload with body_markdown

### 前端（Task 4 待補）

- `<L2Panel>`：右側 slide-in，react-markdown + remark-gfm render
- `<TermTooltip>` 加 prop `l2TopicId?`，有值時右下顯示「看完整說明 →」

## 關鍵檔案

- [backend/src/alpha_lab/education/loader.py](../../../../backend/src/alpha_lab/education/loader.py)
- [backend/src/alpha_lab/education/l2/](../../../../backend/src/alpha_lab/education/l2/)
- [backend/src/alpha_lab/schemas/education.py](../../../../backend/src/alpha_lab/schemas/education.py)

## 修改時注意事項

- **新增 topic**：在 `education/l2/` 丟一份新 .md，frontmatter 要備 `id / title / related_terms`；重啟 backend 或跑 `clear_cache()` 測試才會生效
- **檔名 vs id**：若 frontmatter `id` 缺，loader fallback 用檔名（不含副檔名）。維持一致較不易出錯
- **related_terms** 目前前端只顯示、不做跳轉；Phase 5 / 6 可延伸
- **內容風格**：以「我是初學者，但我不是笨蛋」的語氣；先給一句話定義、再深入，盡量用表格與清單避免大段字
- **勿放敏感 / 連結到外部付費內容**（私人工具，但保持乾淨）
