from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = Path(__file__).resolve().parents[2]

SUMMARY_WORKBOOK = Path(
    os.getenv(
        "SUMMARY_WORKBOOK",
        str(PROJECT_DIR / "民族团结进步促进法舆情统计最终版_非支持原话全量汇总最终版.xlsx"),
    )
)
DETAIL_DIR = Path(
    os.getenv(
        "DETAIL_DIR",
        str(PROJECT_DIR / "细节表"),
    )
)
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data.sqlite3")))
