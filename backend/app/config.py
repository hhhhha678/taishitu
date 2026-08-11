from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
SUMMARY_WORKBOOK = Path(
    os.getenv(
        "SUMMARY_WORKBOOK",
        r"C:\Users\71017\OneDrive\桌面\动态态势图\民族团结进步促进法舆情统计最终版.xlsx",
    )
)
DETAIL_DIR = Path(
    os.getenv(
        "DETAIL_DIR",
        r"C:\Users\71017\OneDrive\桌面\动态态势图\细节表",
    )
)
