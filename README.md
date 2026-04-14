# alpha-lab

台股長線投資個人工具，整合數據面板、選股篩選、多因子組合推薦與嵌入式教學系統。

## 結構

- `frontend/` — React + Vite + TypeScript UI
- `backend/` — FastAPI + Python 資料抓取與分析
- `data/` — 本地數據層（SQLite + 分析報告，不 commit）
- `docs/` — 設計文件、使用者指南

## 設計文件

- [Design Spec](docs/superpowers/specs/2026-04-14-alpha-lab-design.md)
- [User Guide](docs/USER_GUIDE.md)

## 開發

```bash
# Backend
cd backend
uv sync
uvicorn alpha_lab.api.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm dev
```

## 授權

個人專案，暫無授權條款。
