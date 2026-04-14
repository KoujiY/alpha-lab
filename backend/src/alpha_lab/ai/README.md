# AI 整合模組（預留）

此模組於 Phase 0 暫未實作，預留給未來 Phase 7：Claude API 自動化分析整合。

## 規劃內容

- `client.py` — Anthropic SDK wrapper（含 prompt caching）
- `prompts/` — 系統提示範本
  - `stock_analyzer.md` — 個股分析角色
  - `portfolio_recommender.md` — 組合推薦角色
  - `events_summarizer.md` — 事件摘要角色
- `analyzers/` — 對應四種報告類型的自動化生成邏輯

## 初期替代方案

Phase 0-6 期間，上述分析工作由 Claude Code（對話式）處理。Claude Code 讀取 `data/reports/index.json` 與 `data/alpha_lab.db`，產出 Markdown 報告到 `data/reports/analysis/`。
