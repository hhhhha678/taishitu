from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .config import DETAIL_DIR, SUMMARY_WORKBOOK


REGION_PROVINCES = {
    "内蒙古、河北及东北": ["内蒙古", "河北", "辽宁", "吉林", "黑龙江"],
    "新疆": ["新疆"],
    "青海、西藏": ["青海", "西藏"],
    "四川、甘肃民族地区": ["四川", "甘肃"],
    "云南东中部民族地区": ["云南"],
    "云南西部民族地区": ["云南"],
    "广东、广西、海南": ["广东", "广西", "海南"],
    "宁夏、贵州、重庆、湖南、湖北、浙江": ["宁夏", "贵州", "重庆", "湖南", "湖北", "浙江"],
}

PLATFORM_ALIASES = {
    "微博/热榜": ["微博", "热榜"],
    "微信公众号/视频号": ["微信", "公众号", "视频号"],
    "抖音等视频平台": ["抖音", "西瓜", "短视频"],
    "快手": ["快手"],
    "小红书/豆瓣等平台": ["小红书", "豆瓣"],
    "知乎/B站/百度知道": ["知乎", "哔哩哔哩", "B站", "百度知道"],
    "贴吧/头条/新闻评论": ["贴吧", "头条", "新闻"],
}

NON_SUPPORT_COLUMNS = [
    "咨询疑问",
    "担忧影响",
    "明确批评",
    "投诉维权",
    "实施问题",
    "公平争议",
    "歧视偏见",
    "不了解该法律",
]

ATTITUDE_COLUMNS = [
    "支持认可",
    "中性信息",
    *NON_SUPPORT_COLUMNS,
    "参与建议",
    "待核实",
    "其他/未分类",
]

DETAIL_SHEET_TOKENS = ("公众舆情明细", "有效舆情明细", "公众评论明细", "扁平化数据")


def _clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _to_int(value: Any) -> int:
    text = _clean_text(value).replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _to_ratio(value: Any) -> float:
    text = _clean_text(value)
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _load_sheet(path: Path, index: int, header_row: int) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name=index, header=header_row).dropna(how="all")
    frame.columns = [_clean_text(col) for col in frame.columns]
    return frame


def _pick_value(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _clean_text(record.get(key, ""))
        if value:
            return value
    return ""


def _find_header_row(frame: pd.DataFrame) -> int | None:
    for idx in range(min(len(frame), 16)):
        row = [_clean_text(value) for value in frame.iloc[idx].tolist()]
        score = 0
        if any("发布日期" in cell or "发布时间" in cell for cell in row):
            score += 1
        if any("平台" in cell for cell in row):
            score += 1
        if any("地区" in cell for cell in row):
            score += 1
        if any("语言" in cell for cell in row):
            score += 1
        if any("态度" in cell or "意见类型" in cell for cell in row):
            score += 1
        if any("原文" in cell or "摘录" in cell or "标题" in cell or "摘要" in cell for cell in row):
            score += 1
        if score >= 4:
            return idx
    return None


def _normalize_platform(platform_name: str) -> str:
    name = _clean_text(platform_name)
    for group, aliases in PLATFORM_ALIASES.items():
        if any(alias in name for alias in aliases):
            return group
    return name or "未标注平台"


def _normalize_region(region_name: str) -> str:
    name = _clean_text(region_name)
    for group, provinces in REGION_PROVINCES.items():
        if group in name or any(province in name for province in provinces):
            return group
    if any(token in name for token in ("全国", "境外", "台湾")):
        return "全国议题/境外"
    return name or "未标注地区"


def _parse_datetime(value: str) -> tuple[str, str]:
    text = _clean_text(value)
    if not text:
        return "", ""
    try:
        dt = pd.to_datetime(text).to_pydatetime()
        return dt.isoformat(), dt.date().isoformat()
    except Exception:
        return "", ""


def _sample_text(record: dict[str, Any]) -> str:
    return _pick_value(
        record,
        "原文证据摘录",
        "评论原文",
        "中文译文",
        "原文摘录",
        "客观摘要",
        "摘要",
        "标题/主题",
        "标题/主题（母帖）",
        "标题",
    )


def _read_detail_records(detail_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(detail_dir.glob("*.xlsx")):
        workbook = pd.ExcelFile(path)
        for sheet_name in workbook.sheet_names:
            if not any(token in sheet_name for token in DETAIL_SHEET_TOKENS):
                continue
            raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
            header_row = _find_header_row(raw)
            if header_row is None:
                continue
            frame = pd.read_excel(path, sheet_name=sheet_name, header=header_row).dropna(how="all")
            frame.columns = [_clean_text(col) for col in frame.columns]
            for row in frame.to_dict(orient="records"):
                attitude = _pick_value(row, "意见类型", "态度", "公众态度")
                title = _pick_value(row, "标题/主题", "标题/主题（母帖）", "标题")
                text = _sample_text(row)
                platform = _pick_value(row, "平台/网站", "平台或网站", "平台")
                if not (attitude or title or text or platform):
                    continue
                published_at, date = _parse_datetime(_pick_value(row, "发布日期", "发布时间"))
                region = _pick_value(row, "涉及地区", "地区", "来源地区")
                record = {
                    "source_file": path.name,
                    "sheet_name": sheet_name,
                    "published_at": published_at,
                    "date": date,
                    "platform": platform or "未标注平台",
                    "platform_group": _normalize_platform(platform),
                    "region": region or "未标注地区",
                    "region_group": _normalize_region(region),
                    "language": _pick_value(row, "原始语言", "语言") or "未标注语言",
                    "title": title,
                    "quote": _pick_value(row, "原文证据摘录", "评论原文", "原文摘录"),
                    "summary": _pick_value(row, "客观摘要", "摘要", "中文译文"),
                    "attitude": attitude or "未分类",
                    "topic": _pick_value(row, "问题议题", "议题"),
                    "source": _pick_value(row, "采集来源"),
                    "account": _pick_value(row, "账号或栏目名称", "账号或发布单位", "账号名称"),
                    "link": _pick_value(row, "原帖/原文链接", "原始链接", "链接"),
                    "likes": _to_int(row.get("点赞量")),
                    "comments": _to_int(row.get("评论量")),
                    "shares": _to_int(row.get("转发量")),
                }
                if not (record["attitude"] != "未分类" or record["quote"] or record["summary"] or record["title"]):
                    continue
                records.append(record)
    records.sort(key=lambda item: (item["published_at"] or "", item["source_file"], item["sheet_name"]))
    return records


def _build_timeline(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for item in records:
        if not item["date"]:
            continue
        bucket = buckets.setdefault(
            item["date"],
            {
                "date": item["date"],
                "count": 0,
                "non_support": 0,
                "platforms": Counter(),
                "regions": Counter(),
            },
        )
        bucket["count"] += 1
        if item["attitude"] in NON_SUPPORT_COLUMNS:
            bucket["non_support"] += 1
        bucket["platforms"][item["platform_group"]] += 1
        bucket["regions"][item["region_group"]] += 1

    timeline = []
    for date in sorted(buckets):
        item = buckets[date]
        timeline.append(
            {
                "date": date,
                "count": item["count"],
                "non_support": item["non_support"],
                "top_platform": item["platforms"].most_common(1)[0][0] if item["platforms"] else "未标注平台",
                "top_region": item["regions"].most_common(1)[0][0] if item["regions"] else "未标注地区",
            }
        )
    return timeline


def _build_feed(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    feed = []
    for item in records:
        text = item["quote"] or item["summary"] or item["title"]
        if not text:
            continue
        feed.append(
            {
                "published_at": item["published_at"],
                "date": item["date"],
                "platform": item["platform"],
                "platform_group": item["platform_group"],
                "region": item["region"],
                "region_group": item["region_group"],
                "language": item["language"],
                "attitude": item["attitude"],
                "title": item["title"],
                "text": text,
                "topic": item["topic"],
                "likes": item["likes"],
                "comments": item["comments"],
                "shares": item["shares"],
            }
        )
    return feed


def _build_platform_samples(feed: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in feed:
        grouped[item["platform_group"]].append(item)
    result = {}
    for group, items in grouped.items():
        result[group] = sorted(
            items,
            key=lambda item: (item["likes"] + item["comments"] + item["shares"], item["published_at"]),
            reverse=True,
        )[:5]
    return result


def _sort_samples(items: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (item["likes"] + item["comments"] + item["shares"], item["published_at"]),
        reverse=True,
    )[:limit]


def _language_token(label: str) -> str:
    token = _clean_text(label).split("（")[0].replace("/其他", "").replace("/文", "")
    aliases = {
        "中文/普通话": "汉",
        "维吾尔语": "维吾尔",
        "藏语": "藏",
        "彝语": "彝",
        "蒙古语": "蒙古",
        "表情符号": "表情",
    }
    return aliases.get(token, token)


def _overview_metrics(summary_rows: list[list[Any]], language_frame: pd.DataFrame) -> list[dict[str, Any]]:
    platform_total = _to_int(summary_rows[8][0])
    region_total = _to_int(summary_rows[8][5])
    source_total = _to_int(summary_rows[13][5])
    viewed_total = _to_int(summary_rows[13][10])
    minor_language_total = 0
    for _, row in language_frame.iterrows():
        label = _clean_text(row.iloc[0])
        if not label or "中文/普通话" in label or "表情符号" in label:
            continue
        minor_language_total += _to_int(row.iloc[1])
    return [
        {"label": "公众意见总量", "value": platform_total},
        {"label": "可归属地区意见量", "value": region_total},
        {"label": "非支持/非肯定量", "value": 305},
        {"label": "监测来源数", "value": source_total},
        {"label": "查看信息数", "value": viewed_total},
        {"label": "少数民族语言样本", "value": minor_language_total},
    ]


@dataclass
class DashboardRepository:
    cached_signature: tuple[float, float] | None = None
    cached_payload: dict[str, Any] | None = None

    def get_dashboard(self) -> dict[str, Any]:
        signature = self._signature()
        if self.cached_payload is not None and signature == self.cached_signature:
            return self.cached_payload
        payload = self._build_dashboard()
        self.cached_signature = signature
        self.cached_payload = payload
        return payload

    def _signature(self) -> tuple[float, float]:
        workbook_mtime = SUMMARY_WORKBOOK.stat().st_mtime
        detail_latest = max((path.stat().st_mtime for path in DETAIL_DIR.glob("*.xlsx")), default=0.0)
        return workbook_mtime, detail_latest

    def _build_dashboard(self) -> dict[str, Any]:
        raw_summary = pd.read_excel(SUMMARY_WORKBOOK, sheet_name=0, header=None).fillna("")
        summary_rows = raw_summary.values.tolist()
        platform_frame = _load_sheet(SUMMARY_WORKBOOK, 1, 3)
        region_frame = _load_sheet(SUMMARY_WORKBOOK, 2, 3)
        language_frame = _load_sheet(SUMMARY_WORKBOOK, 3, 8)
        monitor_frame = _load_sheet(SUMMARY_WORKBOOK, 11, 3)
        viewed_frame = _load_sheet(SUMMARY_WORKBOOK, 12, 3)
        non_support_frame = _load_sheet(SUMMARY_WORKBOOK, 13, 3)

        detail_records = _read_detail_records(DETAIL_DIR)
        feed = _build_feed(detail_records)
        timeline = _build_timeline(detail_records)
        platform_samples = _build_platform_samples(feed)

        platform_total_row = platform_frame[platform_frame["平台"] == "合计"].iloc[0]
        total_posts = _to_int(platform_total_row["有效公众意见总数"])
        non_support_total = int(non_support_frame[non_support_frame["类别"] == "合计"]["数量"].iloc[0])
        support_total = _to_int(platform_total_row["支持认可"])
        neutral_total = total_posts - support_total - non_support_total

        overall_attitudes = [
            {"name": "支持认可", "value": support_total},
            {"name": "中性/其他", "value": max(neutral_total, 0)},
            {"name": "非支持/非肯定", "value": non_support_total},
        ]

        source_lookup = {
            row["类别"]: _to_int(row["数量"])
            for _, row in monitor_frame.iterrows()
            if _clean_text(row["类别"]) and row["类别"] != "合计"
        }
        viewed_lookup = {
            row["类别"]: _to_int(row["数量"])
            for _, row in viewed_frame.iterrows()
            if _clean_text(row["类别"]) and row["类别"] != "合计"
        }

        platform_feed: dict[str, list[dict[str, Any]]] = defaultdict(list)
        region_feed: dict[str, list[dict[str, Any]]] = defaultdict(list)
        region_platform_counts: dict[str, Counter] = defaultdict(Counter)
        for item in feed:
            platform_feed[item["platform_group"]].append(item)
            region_feed[item["region_group"]].append(item)
            region_platform_counts[item["region_group"]][item["platform_group"]] += 1

        platforms = []
        for _, row in platform_frame.iterrows():
            name = _clean_text(row["平台"])
            if not name or name == "合计":
                continue
            row_total = _to_int(row["有效公众意见总数"])
            non_support = sum(_to_int(row[col]) for col in NON_SUPPORT_COLUMNS if col in row)
            attitude_rows = [
                {"name": attitude, "value": _to_int(row[attitude])}
                for attitude in ATTITUDE_COLUMNS
                if attitude in row and _to_int(row[attitude]) > 0
            ]
            platforms.append(
                {
                    "name": name,
                    "total": row_total,
                    "share": round(row_total / total_posts, 4) if total_posts else 0,
                    "support": _to_int(row["支持认可"]),
                    "neutral": _to_int(row["中性信息"]),
                    "non_support": non_support,
                    "participation": _to_int(row["参与建议"]),
                    "source_count": source_lookup.get(name, 0),
                    "view_count": viewed_lookup.get(name, 0),
                    "attitudes": attitude_rows,
                    "top_attitude": max(attitude_rows, key=lambda item: item["value"])["name"] if attitude_rows else "",
                    "sample_comments": platform_samples.get(name, []),
                    "linked_sample_count": len(platform_feed.get(name, [])),
                }
            )
        platforms.sort(key=lambda item: item["total"], reverse=True)

        province_heat: dict[str, int] = defaultdict(int)
        regions = []
        for _, row in region_frame.iterrows():
            name = _clean_text(row["地区分工组"])
            if not name or name == "合计":
                continue
            total = _to_int(row["有效公众意见总数"])
            non_support = sum(_to_int(row[col]) for col in NON_SUPPORT_COLUMNS if col in row)
            provinces = REGION_PROVINCES.get(name, [name])
            attitude_rows = [
                {"name": attitude, "value": _to_int(row[attitude])}
                for attitude in ATTITUDE_COLUMNS
                if attitude in row and _to_int(row[attitude]) > 0
            ]
            for province in provinces:
                province_heat[province] += total
            regions.append(
                {
                    "name": name,
                    "total": total,
                    "support": _to_int(row["支持认可"]),
                    "non_support": non_support,
                    "provinces": provinces,
                    "attitudes": attitude_rows,
                    "top_platforms": [
                        {"name": platform, "value": count}
                        for platform, count in region_platform_counts.get(name, Counter()).most_common(4)
                    ],
                    "sample_comments": _sort_samples(region_feed.get(name, [])),
                    "linked_sample_count": len(region_feed.get(name, [])),
                }
            )
        regions.sort(key=lambda item: item["total"], reverse=True)

        language_rows = []
        for _, row in language_frame.iloc[:, :3].iterrows():
            name = _clean_text(row.iloc[0])
            if not name or name == "平台维度语言分布":
                continue
            value = _to_int(row.iloc[1])
            if value == 0 and "中文/普通话" not in name:
                continue
            lookup_name = _language_token(name)
            language_rows.append(
                {
                    "name": name,
                    "value": value,
                    "ratio": round(_to_ratio(row.iloc[2]), 4),
                    "samples": [item for item in feed if lookup_name and lookup_name in item["language"]][:5],
                }
            )

        non_support_breakdown = []
        for _, row in non_support_frame.iterrows():
            name = _clean_text(row["类别"])
            if not name or name == "合计":
                continue
            non_support_breakdown.append({"name": name, "value": _to_int(row["数量"])})

        date_range = {
            "from": timeline[0]["date"] if timeline else "",
            "to": timeline[-1]["date"] if timeline else "",
        }

        return {
            "title": "民族相关网络舆情动态态势感知大屏",
            "subtitle": "第一阶段｜基于历史监测数据的非实时动态态势展示",
            "date_range": date_range,
            "data_notice": "当前展示基于已整理历史监测数据，页面动态为历史数据联动展示，不表示实时新增采集。",
            "metrics": _overview_metrics(summary_rows, language_frame),
            "map": {
                "province_heat": [{"name": key, "value": value} for key, value in province_heat.items()],
                "regions": regions,
            },
            "platforms": platforms,
            "languages": language_rows,
            "overall_attitudes": overall_attitudes,
            "non_support_breakdown": non_support_breakdown,
            "timeline": timeline,
            "feed": feed[:400],
        }


repository = DashboardRepository()
