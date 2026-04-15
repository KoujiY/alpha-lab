---
domain: features/education
updated: 2026-04-17
related: [../data-panel/ui-layout.md, l2-panel.md]
---

# 術語 Tooltip（L1）

## 目的

符合 spec §10「兩層教學」的 L1：hover 顯示 1-3 行簡短定義，降低初學者閱讀成本。L2 側邊面板於 Phase 4（教學系統完整版）實作。

## 現行實作

- **資料**：`backend/src/alpha_lab/glossary/terms.yaml`，每條 `{term, short, detail, related}`，由 `GET /api/glossary` 一次取回所有（約 15 條，量小）
- **前端**：`useGlossary()` hook（TanStack Query，staleTime 10 min）快取整張表；`<TermTooltip term="PE">本益比 (PE)</TermTooltip>` 以 `<abbr>` + 虛線下劃標示可互動，mouseenter/focus 觸發
- **fallback**：glossary 未涵蓋該 key → `<abbr title={key}>` 只顯示 key 本身，不會報錯

## v1 術語清單（15 條）

PE、PB、EPS、ROE、毛利率、殖利率、月營收、YoY、MoM、三大法人、外資、投信、自營商、融資、融券

## 關鍵檔案

- [backend/src/alpha_lab/glossary/terms.yaml](../../../backend/src/alpha_lab/glossary/terms.yaml)
- [backend/src/alpha_lab/glossary/loader.py](../../../backend/src/alpha_lab/glossary/loader.py)
- [backend/src/alpha_lab/api/routes/glossary.py](../../../backend/src/alpha_lab/api/routes/glossary.py)
- [frontend/src/components/TermTooltip.tsx](../../../frontend/src/components/TermTooltip.tsx)
- [frontend/src/hooks/useGlossary.ts](../../../frontend/src/hooks/useGlossary.ts)

## 修改時注意事項

- 術語 key 建議用中文（例：`毛利率`）或英文縮寫（例：`PE`）；加詞時兩邊都更新：terms.yaml + 測試 `test_terms_v1.py` EXPECTED_TERMS
- `short` 長度上限 200 字（schema 限制），實務建議 1-2 句 40-80 字
- Phase 4 L2 已實作：`<TermTooltip l2TopicId="PE">` 在 tooltip 右下多一顆「看完整說明 →」按鈕，點擊呼叫 `L2PanelContext.openTopic(id)` 打開右側 slide-in 詳解；詳見 [l2-panel.md](l2-panel.md)
- L1（hover）與 L2（click）互斥：開 L2 時 tooltip 收起，避免兩層 UI 疊字
