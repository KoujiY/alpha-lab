"""compute_scores CLI 煙霧測試。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_help_runs() -> None:
    repo_backend = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/compute_scores.py", "-h"],
        cwd=repo_backend,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Compute factor scores" in result.stdout
