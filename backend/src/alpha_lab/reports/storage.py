"""Reports 低階檔案 I/O（Phase 4）。"""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

from alpha_lab.schemas.report import ReportMeta

_DEFAULT_ROOT = Path(__file__).resolve().parents[4] / "data" / "reports"


def get_reports_root() -> Path:
    """讀取 reports 根目錄；環境變數優先，否則專案 `data/reports`。"""

    env_root = os.environ.get("ALPHA_LAB_REPORTS_ROOT")
    if env_root:
        return Path(env_root)
    return _DEFAULT_ROOT


def _ensure_dirs(root: Path) -> None:
    (root / "analysis").mkdir(parents=True, exist_ok=True)
    (root / "summaries").mkdir(parents=True, exist_ok=True)


def load_index() -> list[ReportMeta]:
    root = get_reports_root()
    index_path = root / "index.json"
    if not index_path.exists():
        return []
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    reports_raw = raw.get("reports", []) if isinstance(raw, dict) else []
    return [ReportMeta(**item) for item in reports_raw]


def save_index(items: list[ReportMeta]) -> None:
    root = get_reports_root()
    _ensure_dirs(root)
    payload = {
        "updated_at": datetime.now(UTC).isoformat(),
        "reports": [item.model_dump(mode="json") for item in items],
    }
    (root / "index.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def upsert_in_index(meta: ReportMeta) -> None:
    """加入或覆蓋同 id 的 meta。"""

    items = load_index()
    items = [m for m in items if m.id != meta.id]
    items.append(meta)
    # 以 date 排序新 → 舊，便於前端列表
    items.sort(key=lambda m: (m.date, m.id), reverse=True)
    save_index(items)


def write_report_markdown(
    report_id: str,
    body: str,
    frontmatter: dict[str, object],
    *,
    relative_path: str | None = None,
) -> Path:
    """寫入報告 markdown；若提供 relative_path 則使用該路徑，否則 analysis/<id>.md。"""

    root = get_reports_root()
    _ensure_dirs(root)
    if relative_path:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path = root / "analysis" / f"{report_id}.md"
    fm_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()
    content = f"---\n{fm_yaml}\n---\n\n{body.strip()}\n"
    path.write_text(content, encoding="utf-8")
    return path


def read_report_markdown(
    report_id: str, *, relative_path: str | None = None
) -> tuple[dict[str, object], str] | None:
    """回 (frontmatter_dict, body) 或 None。

    ``relative_path`` 若提供，使用 ``reports_root / relative_path`` 定位檔案；
    否則退回舊行為 ``analysis/{report_id}.md``。
    """

    root = get_reports_root()
    if relative_path:
        path = root / relative_path
    else:
        path = root / "analysis" / f"{report_id}.md"
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: missing leading frontmatter marker")
    try:
        end_idx = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"{path}: missing closing frontmatter marker") from exc

    fm = yaml.safe_load("\n".join(lines[1:end_idx])) or {}
    if not isinstance(fm, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    body = "\n".join(lines[end_idx + 1 :]).strip()
    return fm, body


def append_summary(iso_date: str, summary_line: str) -> None:
    """`summaries/<date>.json` 是一個 list of {summary}，append 一筆。"""

    root = get_reports_root()
    _ensure_dirs(root)
    path = root / "summaries" / f"{iso_date}.json"
    existing: list[dict[str, str]] = []
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = [x for x in loaded if isinstance(x, dict)]
        except json.JSONDecodeError:
            existing = []
    existing.append({"summary": summary_line})
    path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def delete_report_files(report_id: str) -> bool:
    """刪報告 markdown 檔案並從 index.json 移除。回傳是否刪到。"""

    items = load_index()
    target = next((m for m in items if m.id == report_id), None)
    before = len(items)
    items = [m for m in items if m.id != report_id]
    root = get_reports_root()
    if target:
        md_path = root / target.path
    else:
        md_path = root / "analysis" / f"{report_id}.md"
    if md_path.exists():
        md_path.unlink()
    save_index(items)
    return len(items) < before


def update_in_index(report_id: str, updates: dict[str, object]) -> ReportMeta | None:
    """套 updates 到同 id 項目；None = id 不存在。回傳新 meta。"""

    items = load_index()
    target_idx = next((i for i, m in enumerate(items) if m.id == report_id), None)
    if target_idx is None:
        return None
    current = items[target_idx].model_dump()
    current.update(updates)
    updated = ReportMeta(**current)
    items[target_idx] = updated
    save_index(items)
    return updated


def write_daily_markdown(report_date: date, body: str) -> Path:
    """寫入 daily/<YYYY-MM-DD>.md。覆寫同日既有檔案。"""
    root = get_reports_root()
    daily_dir = root / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    path = daily_dir / f"{report_date.isoformat()}.md"
    path.write_text(body.strip() + "\n", encoding="utf-8")
    return path


def read_daily_markdown(report_date: date) -> str | None:
    """讀取 daily/<YYYY-MM-DD>.md 內容，不存在回傳 None。"""
    root = get_reports_root()
    path = root / "daily" / f"{report_date.isoformat()}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")
