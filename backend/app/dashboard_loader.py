from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

import pandas as pd

from .config import DETAIL_DIR, SUMMARY_WORKBOOK


REGION_PROVINCES = {
    "内蒙古、河北及东北": ["内蒙古", "河北", "辽宁", "吉林", "黑龙江"],
    "新疆": ["新疆"],
    "青海、西藏": ["青海", "西藏"],
    "四川、甘肃民族地区": ["四川", "甘肃"],
    "云南东中部民族地区": ["云南"],
    "云南西部民族地区": ["云南"],
    "广东": ["广东"],
    "广西": ["广西"],
    "海南": ["海南"],
    "宁夏、贵州、重庆、湖南、湖北、浙江": ["宁夏", "贵州", "重庆", "湖南", "湖北", "浙江"],
    "北京": ["北京"],
    "天津": ["天津"],
    "上海": ["上海"],
    "山东": ["山东"],
    "福建": ["福建"],
    "山西": ["山西"],
    "河南": ["河南"],
    "江西": ["江西"],
    "江苏": ["江苏"],
    "安徽": ["安徽"],
    "陕西": ["陕西"],
}

REGION_DISPLAY_ORDER = list(REGION_PROVINCES)

REGION_ALIASES = {
    "江西": ["上饶", "江西"],
    "新疆": ["新疆维吾尔自治区", "新疆全区", "昌吉", "伊犁", "巴音郭楞", "博尔塔拉"],
    "青海、西藏": ["青海", "西藏", "西宁"],
    "四川、甘肃民族地区": ["四川", "甘肃", "凉山", "阿坝", "甘南", "临夏", "肃北", "肃南", "东乡", "积石山"],
    "内蒙古、河北及东北": ["内蒙古", "河北", "辽宁", "吉林", "黑龙江"],
    "云南东中部民族地区": ["文山", "楚雄", "峨山"],
    "云南西部民族地区": ["沧源", "云南"],
}

REGION_SKIP_NAMES = {
    "地区分工组/补测省份",
    "原地区分工组小计",
    "新增补测省份小计",
    "地区维度合计",
    "说明",
}

PROVINCE_STAT_SKIP_NAMES = {"省级行政区", "地区维度总计"}

PLATFORM_ALIASES = {
    "微博/热榜": ["微博", "热榜"],
    "微信公众号/视频号": ["微信", "公众号", "视频号"],
    "抖音等视频平台": ["抖音", "西瓜", "短视频"],
    "快手": ["快手"],
    "小红书/豆瓣等平台": ["小红书", "豆瓣"],
    "知乎/B站/百度知道": ["知乎", "哔哩哔哩", "B站", "百度知道"],
    "贴吧/头条/新闻评论": ["贴吧", "头条", "新闻"],
}

ATTITUDE_ALIASES = {
    "中性信息": "中性/观点不明",
    "支持认可法律": "支持认可",
    "官方政策信息": "支持认可",
    "官方传播信息": "支持认可",
    "官方实施信息": "支持认可",
    "媒体传播信息": "支持认可",
    "媒体报道": "支持认可",
    "公众讨论母帖": "中性/观点不明",
    "投诉维权": "投诉维权/举报",
    "待核实信息": "其他/专题讨论/未分类",
    "无法判断": "其他/专题讨论/未分类",
    "无关评论": "其他/专题讨论/未分类",
}

NON_SUPPORT_COLUMNS = [
    "咨询疑问",
    "担忧影响",
    "明确批评",
    "投诉维权/举报",
    "实施问题",
    "公平争议",
    "歧视偏见",
    "不了解该法律",
]

ATTITUDE_COLUMNS = [
    "支持认可",
    "中性/观点不明",
    *NON_SUPPORT_COLUMNS,
    "参与建议",
    "其他/专题讨论/未分类",
]

DETAIL_SHEET_TOKENS = ("公众舆情明细", "有效舆情明细", "公众评论明细", "扁平化数据", "非支持来源与原话")


def _clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _to_int(value: Any) -> int:
    text = _clean_text(value)
    match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", text)
    if not match:
        return 0
    try:
        return int(float(match.group(0).replace(",", "")))
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


def _load_sheet(path: Path, sheet_name: str, header_row: int) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name=sheet_name, header=header_row).dropna(how="all")
    frame.columns = [_clean_text(col) for col in frame.columns]
    return frame


def _pick_value(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _clean_text(record.get(key, ""))
        if value:
            return value
    return ""


def _find_header_row(frame: pd.DataFrame) -> int | None:
    for idx in range(min(len(frame), 24)):
        row = [_clean_text(value) for value in frame.iloc[idx].tolist()]
        score = 0
        if any("发布日期" in cell or "发布时间" in cell or "采集日期" in cell for cell in row):
            score += 1
        if any("平台" in cell for cell in row):
            score += 1
        if any("地区" in cell or "省份" in cell for cell in row):
            score += 1
        if any("语言" in cell for cell in row):
            score += 1
        if any("态度" in cell or "意见类型" in cell for cell in row):
            score += 1
        if any("原文" in cell or "原话" in cell or "摘录" in cell or "标题" in cell or "摘要" in cell for cell in row):
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
    for group, aliases in REGION_ALIASES.items():
        if any(alias in name for alias in aliases):
            return group
    for group, provinces in REGION_PROVINCES.items():
        if group in name or any(province in name for province in provinces):
            return group
    if any(token in name for token in ("全国", "境外", "台湾")):
        return "全国议题/境外"
    return name or "未标注地区"


def _normalize_attitude(attitude_name: str) -> str:
    name = _clean_text(attitude_name)
    if not name:
        return "未分类"
    for source, target in ATTITUDE_ALIASES.items():
        if source in name:
            return target
    for attitude in ATTITUDE_COLUMNS:
        if attitude in name:
            return attitude
    return name


def _parse_datetime(value: str) -> tuple[str, str]:
    text = _clean_text(value)
    if not text:
        return "", ""
    try:
        dt = pd.to_datetime(text).to_pydatetime()
        if not (2020 <= dt.year <= 2035):
            return "", ""
        return dt.isoformat(), dt.date().isoformat()
    except Exception:
        return "", ""


def _sample_text(record: dict[str, Any]) -> str:
    return _pick_value(
        record,
        "原文证据摘录",
        "原话/代表性原话",
        "评论原文",
        "中文译文",
        "原文摘录",
        "客观摘要",
        "摘要",
        "标题/主题",
        "母帖/母视频/标题",
        "标题",
    )


def _read_records_from_table(frame: pd.DataFrame, source_file: str, sheet_name: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    frame.columns = [_clean_text(col) for col in frame.columns]
    for row in frame.to_dict(orient="records"):
        attitude = _normalize_attitude(_pick_value(row, "态度类别（原表/复核后）", "意见类型", "态度", "公众态度"))
        title = _pick_value(row, "标题/主题", "标题/主题（母帖）", "母帖/母视频/标题", "标题")
        text = _sample_text(row)
        platform = _pick_value(row, "平台/网站", "平台或网站", "平台", "来源平台")
        if not (attitude or title or text or platform):
            continue
        published_at, date = _parse_datetime(_pick_value(row, "发布日期", "发布时间", "发布时间/采集日期", "采集日期"))
        region = _pick_value(row, "涉及地区", "来源表地区/涉及地区", "地区", "来源地区", "省份")
        record = {
            "source_file": source_file,
            "sheet_name": sheet_name,
            "published_at": published_at,
            "date": date,
            "platform": platform or "未标注平台",
            "platform_group": _normalize_platform(platform),
            "region": region or "未标注地区",
            "region_group": _normalize_region(region),
            "language": _pick_value(row, "原始语言", "语言") or "未标注语言",
            "title": title,
            "quote": _pick_value(row, "原文证据摘录", "原话/代表性原话", "评论原文", "原文摘录"),
            "summary": _pick_value(row, "客观摘要", "摘要", "中文译文"),
            "attitude": attitude,
            "topic": _pick_value(row, "问题议题", "具体议题", "议题"),
            "source": _pick_value(row, "采集来源", "证据类型/采集来源"),
            "account": _pick_value(row, "账号或栏目名称", "账号或发布单位", "账号名称", "账号/栏目"),
            "link": _pick_value(row, "原帖/原文链接", "原始链接/证据入口", "原始链接", "链接"),
            "likes": _to_int(row.get("点赞量")),
            "comments": _to_int(row.get("评论量")),
            "shares": _to_int(row.get("转发量")),
        }
        if not (record["attitude"] != "未分类" or record["quote"] or record["summary"] or record["title"]):
            continue
        records.append(record)
    return records


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
            records.extend(_read_records_from_table(frame, path.name, sheet_name))
    records.sort(key=lambda item: (item["published_at"] or "", item["source_file"], item["sheet_name"]))
    return _unique_records(records)


def _read_evidence_records() -> list[dict[str, Any]]:
    try:
        frame = pd.read_excel(SUMMARY_WORKBOOK, sheet_name="非支持来源与原话", header=9).dropna(how="all")
    except Exception:
        return []
    return _read_records_from_table(frame, SUMMARY_WORKBOOK.name, "非支持来源与原话")


def _unique_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for item in records:
        text = item.get("quote") or item.get("summary") or item.get("title") or item.get("text") or ""
        key = (item.get("date", ""), item.get("platform", ""), item.get("region", ""), item.get("attitude", ""), text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


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
        result[group] = _sort_samples(items)
    return result


def _sort_samples(items: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (item["likes"] + item["comments"] + item["shares"], item["published_at"]),
        reverse=True,
    )[:limit]


def _balanced_feed(feed: list[dict[str, Any]], regions: list[dict[str, Any]], platforms: list[dict[str, Any]], limit: int = 400) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    def add(item: dict[str, Any]) -> None:
        key = (item.get("date", ""), item.get("platform", ""), item.get("region", ""), item.get("attitude", ""), item.get("text", ""))
        if key in seen:
            return
        seen.add(key)
        selected.append(item)

    for region in regions:
        for item in feed:
            if item["region_group"] == region["name"] or item["region"] == region["name"]:
                add(item)
                break
    for platform in platforms:
        for item in feed:
            if item["platform_group"] == platform["name"] or item["platform"] == platform["name"]:
                add(item)
                break
    for item in feed:
        add(item)
    return selected


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
    platform_total = _to_int(summary_rows[7][1])
    region_total = _to_int(summary_rows[7][4])
    source_total = _to_int(summary_rows[10][1])
    viewed_total = _to_int(summary_rows[10][4])
    minor_language_total = 0
    for _, row in language_frame.iterrows():
        label = _clean_text(row.iloc[0])
        if not label or label == "合计" or "中文/普通话" in label or "表情符号" in label:
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


def _summary_date_range(summary_rows: list[list[Any]], fallback: dict[str, str]) -> dict[str, str]:
    text = "\n".join(_clean_text(cell) for row in summary_rows for cell in row)
    dates = [pd.to_datetime(match).date().isoformat() for match in re.findall(r"20\d{2}-\d{2}-\d{2}", text)]
    if not dates:
        return fallback
    return {
        "from": fallback.get("from") or min(dates),
        "to": max([fallback.get("to") or "", *dates]),
        "note": "平台维度截至2026-08-05；地区补测扩展至2026-08-11",
    }


def _is_data_row(row: pd.Series, name_key: str, total_key: str) -> bool:
    name = _clean_text(row.get(name_key))
    return bool(name) and name not in REGION_SKIP_NAMES and _to_int(row.get(total_key)) > 0


def _build_attitude_rows(row: pd.Series) -> list[dict[str, Any]]:
    return [
        {"name": attitude, "value": _to_int(row.get(attitude))}
        for attitude in ATTITUDE_COLUMNS
        if _to_int(row.get(attitude)) > 0
    ]


def _read_province_heat() -> dict[str, int]:
    try:
        province_frame = _load_sheet(SUMMARY_WORKBOOK, "省级态度统计", 2)
    except Exception:
        return {}
    heat: dict[str, int] = {}
    for _, row in province_frame.iterrows():
        name = _clean_text(row.get("省级行政区"))
        value = _to_int(row.get("有效公众意见总数"))
        if not name or name in PROVINCE_STAT_SKIP_NAMES or value <= 0:
            continue
        heat[name] = value
    return heat


def _has_province_level_heat(province_heat: dict[str, int], provinces: list[str]) -> bool:
    return any(province in province_heat for province in provinces)


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
        raw_summary = pd.read_excel(SUMMARY_WORKBOOK, sheet_name="统计总览", header=None).fillna("")
        summary_rows = raw_summary.values.tolist()
        platform_frame = _load_sheet(SUMMARY_WORKBOOK, "平台统计", 2)
        region_frame = _load_sheet(SUMMARY_WORKBOOK, "地区统计", 2)
        language_frame = _load_sheet(SUMMARY_WORKBOOK, "语言统计", 2)
        monitor_frame = _load_sheet(SUMMARY_WORKBOOK, "监测来源统计", 2)
        viewed_frame = _load_sheet(SUMMARY_WORKBOOK, "查看信息统计", 2)
        non_support_frame = _load_sheet(SUMMARY_WORKBOOK, "非支持态度统计", 2)

        detail_records = _unique_records([*_read_detail_records(DETAIL_DIR), *_read_evidence_records()])
        feed = _build_feed(detail_records)
        timeline = _build_timeline(detail_records)
        platform_samples = _build_platform_samples(feed)

        platform_total_row = platform_frame[platform_frame["平台"] == "合计"].iloc[0]
        total_posts = _to_int(platform_total_row["有效公众意见总数"])
        support_total = _to_int(platform_total_row["支持认可"])
        non_support_total = 305
        non_support_match = non_support_frame[non_support_frame["类别"] == "平台维度合计"]
        if not non_support_match.empty:
            non_support_total = _to_int(non_support_match.iloc[0]["数量"])
        neutral_total = total_posts - support_total - non_support_total

        overall_attitudes = [
            {"name": "支持认可", "value": support_total},
            {"name": "中性/其他", "value": max(neutral_total, 0)},
            {"name": "非支持/非肯定", "value": non_support_total},
        ]

        source_lookup = {
            row["平台组/地区"]: _to_int(row["数量"])
            for _, row in monitor_frame.iterrows()
            if _clean_text(row.get("平台组/地区")) and row.get("平台组/地区") != "小计"
        }
        viewed_lookup = {
            row["平台组/地区"]: _to_int(row["查看信息量"])
            for _, row in viewed_frame.iterrows()
            if _clean_text(row.get("平台组/地区")) and row.get("平台组/地区") != "小计"
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
            name = _clean_text(row.get("平台"))
            if not _is_data_row(row, "平台", "有效公众意见总数") or name == "合计":
                continue
            row_total = _to_int(row["有效公众意见总数"])
            non_support = sum(_to_int(row.get(col)) for col in NON_SUPPORT_COLUMNS)
            attitude_rows = _build_attitude_rows(row)
            platforms.append(
                {
                    "name": name,
                    "total": row_total,
                    "share": round(row_total / total_posts, 4) if total_posts else 0,
                    "support": _to_int(row["支持认可"]),
                    "neutral": _to_int(row["中性/观点不明"]),
                    "non_support": non_support,
                    "participation": _to_int(row.get("参与建议")),
                    "source_count": source_lookup.get(name, 0),
                    "view_count": viewed_lookup.get(name, 0),
                    "attitudes": attitude_rows,
                    "top_attitude": max(attitude_rows, key=lambda item: item["value"])["name"] if attitude_rows else "",
                    "sample_comments": platform_samples.get(name, [])[:8],
                    "linked_sample_count": len(platform_feed.get(name, [])),
                }
            )
        platforms.sort(key=lambda item: item["total"], reverse=True)

        province_heat: dict[str, int] = defaultdict(int, _read_province_heat())
        regions = []
        seen_regions: set[str] = set()
        for _, row in region_frame.iterrows():
            name = _clean_text(row.get("地区分工组/补测省份"))
            if not _is_data_row(row, "地区分工组/补测省份", "有效公众意见总数") or name in seen_regions:
                continue
            seen_regions.add(name)
            total = _to_int(row.get("有效公众意见总数"))
            non_support = sum(_to_int(row.get(col)) for col in NON_SUPPORT_COLUMNS)
            provinces = REGION_PROVINCES.get(name, [name])
            attitude_rows = _build_attitude_rows(row)
            if not _has_province_level_heat(province_heat, provinces):
                for province in provinces:
                    province_heat[province] = total
            regions.append(
                {
                    "name": name,
                    "total": total,
                    "support": _to_int(row.get("支持认可")),
                    "non_support": non_support,
                    "provinces": provinces,
                    "attitudes": attitude_rows,
                    "top_platforms": [
                        {"name": platform, "value": count}
                        for platform, count in region_platform_counts.get(name, Counter()).most_common(4)
                    ],
                    "sample_comments": _sort_samples(region_feed.get(name, []), 8),
                    "linked_sample_count": len(region_feed.get(name, [])),
                }
            )
        regions.sort(key=lambda item: item["total"], reverse=True)

        language_rows = []
        for _, row in language_frame.iloc[:, :3].iterrows():
            name = _clean_text(row.iloc[0])
            if not name or name == "合计":
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
            name = _clean_text(row.get("类别"))
            value = _to_int(row.get("数量"))
            if not name or name not in NON_SUPPORT_COLUMNS or value <= 0:
                continue
            non_support_breakdown.append({"name": name, "value": value})

        timeline_range = {
            "from": timeline[0]["date"] if timeline else "",
            "to": timeline[-1]["date"] if timeline else "",
        }
        date_range = _summary_date_range(summary_rows, timeline_range)

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
            "feed": _balanced_feed(feed, regions, platforms),
        }


repository = DashboardRepository()
