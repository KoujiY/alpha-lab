# alpha-lab backend

FastAPI 後端：數據抓取、分析、API 提供。

## 開發

```bash
uv sync --all-extras        # 或 pip install -e ".[dev]"
uvicorn alpha_lab.api.main:app --reload
```

## 結構

- `src/alpha_lab/api/` — FastAPI 路由
- `src/alpha_lab/collectors/` — 數據抓取（TWSE、MOPS 等）
- `src/alpha_lab/analysis/` — 多因子評分、組合生成
- `src/alpha_lab/storage/` — SQLAlchemy models、檔案 I/O
- `src/alpha_lab/schemas/` — Pydantic DTO
- `src/alpha_lab/glossary/` — 術語庫（靜態資料）
- `src/alpha_lab/ai/` — 預留 Claude API 整合

## 測試

```bash
pytest                     # 執行測試
ruff check .               # lint
mypy src                   # 型別檢查
```
