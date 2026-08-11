from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import re

from ..storage import (
    add_snapshot,
    create_alert,
    fetch_alerts,
    fetch_comments,
    fetch_posts,
    fetch_snapshots,
    get_topic,
)


NEGATIVE_WORDS = ["差", "慢", "投诉", "不满", "担心", "失望", "延迟", "推诿", "问题", "卡住", "负面"]
POSITIVE_WORDS = ["好", "满意", "及时", "优化", "提升", "顺利", "高效", "落实", "积极"]


def classify_sentiment(text: str) -> str:
    lowered = text.lower()
    negative = sum(1 for word in NEGATIVE_WORDS if word in lowered)
    positive = sum(1 for word in POSITIVE_WORDS if word in lowered)
    if negative > positive:
        return "negative"
    if positive > negative:
        return "positive"
    return "neutral"


def _bucket_key(dt: datetime) -> str:
    minute = (dt.minute // 15) * 15
    return dt.replace(minute=minute, second=0, microsecond=0, tzinfo=timezone.utc).isoformat()


def update_metrics_for_topic(topic_id: int) -> int:
    posts = fetch_posts(topic_id=topic_id, limit=500)
    if not posts:
        return 0

    now = datetime.now(timezone.utc)
    last_day = [post for post in posts if post["published_at"] >= now - timedelta(days=1)]
    grouped: dict[tuple[str, str], list] = defaultdict(list)
    for post in last_day:
        grouped[(post["platform"], _bucket_key(post["published_at"]))].append(post)

    alerts_created = 0
    for (platform, bucket), items in grouped.items():
        total_likes = sum(item["likes"] for item in items)
        total_shares = sum(item["shares"] for item in items)
        total_comments = sum(item["comments_count"] for item in items)
        negative_posts = sum(1 for item in items if item["sentiment"] == "negative")
        add_snapshot(topic_id, platform, bucket, len(items), total_likes, total_shares, total_comments, negative_posts)

    total_posts = len(last_day)
    negative_posts = sum(1 for post in last_day if post["sentiment"] == "negative")
    negative_rate = negative_posts / total_posts if total_posts else 0.0
    recent_posts = [post for post in last_day if post["published_at"] >= now - timedelta(hours=3)]
    if len(recent_posts) >= 4:
        recent_count = len(recent_posts)
        older_count = max(total_posts - recent_count, 1)
        if recent_count >= older_count * 1.5:
            create_alert(topic_id, "volume_spike", "high", f"近3小时声量 {recent_count} 条，高于历史均值。")
            alerts_created += 1
    if negative_rate >= 0.35:
        create_alert(topic_id, "negative_rate", "medium", f"负面占比 {negative_rate:.0%}，需要持续关注。")
        alerts_created += 1

    comments = fetch_comments(topic_id=topic_id, limit=200)
    if comments:
        counter = Counter()
        for item in comments:
            for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", item["content"]):
                if len(token) >= 2:
                    counter[token] += 1
        if counter:
            top_word, freq = counter.most_common(1)[0]
            if freq >= 5:
                create_alert(topic_id, "keyword_hit", "low", f"关键词 {top_word} 出现 {freq} 次。")
                alerts_created += 1
    return alerts_created


def build_dashboard(topic_id: int, bucket_from: str | None = None, bucket_to: str | None = None) -> dict:
    topic = get_topic(topic_id)
    posts = fetch_posts(topic_id=topic_id, limit=500)
    comments = fetch_comments(topic_id=topic_id, limit=500)
    alerts = fetch_alerts(topic_id=topic_id)
    snapshots = fetch_snapshots(topic_id, bucket_from=bucket_from, bucket_to=bucket_to)

    platform_distribution = Counter(post["platform"] for post in posts)
    sentiment_distribution = Counter(post["sentiment"] for post in posts)
    total_posts = len(posts)
    total_comments = len(comments)
    total_likes = sum(post["likes"] for post in posts)
    total_shares = sum(post["shares"] for post in posts)
    negative_rate = (
        sentiment_distribution.get("negative", 0) / total_posts if total_posts else 0.0
    )

    return {
        "topic": topic,
        "total_posts": total_posts,
        "total_comments": total_comments,
        "total_likes": total_likes,
        "total_shares": total_shares,
        "negative_rate": round(negative_rate, 4),
        "alert_count": len(alerts),
        "platform_distribution": [
            {"name": key, "value": value} for key, value in platform_distribution.items()
        ],
        "sentiment_distribution": [
            {"name": key, "value": value} for key, value in sentiment_distribution.items()
        ],
        "snapshots": snapshots,
    }


def build_trends(topic_id: int, platform: str | None = None, sentiment: str | None = None) -> list[dict]:
    posts = fetch_posts(topic_id=topic_id, limit=500)
    rows = []
    for post in posts:
        if platform and post["platform"] != platform:
            continue
        if sentiment and post["sentiment"] != sentiment:
            continue
        bucket = _bucket_key(post["published_at"])
        rows.append(
            {
                "bucket": bucket,
                "platform": post["platform"],
                "posts": 1,
                "likes": post["likes"],
                "shares": post["shares"],
                "comments": post["comments_count"],
                "negative_posts": 1 if post["sentiment"] == "negative" else 0,
            }
        )
    merged: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["bucket"], row["platform"])
        if key not in merged:
            merged[key] = row.copy()
        else:
            merged[key]["posts"] += row["posts"]
            merged[key]["likes"] += row["likes"]
            merged[key]["shares"] += row["shares"]
            merged[key]["comments"] += row["comments"]
            merged[key]["negative_posts"] += row["negative_posts"]
    return sorted(merged.values(), key=lambda item: (item["bucket"], item["platform"]))


def build_comment_insights(topic_id: int) -> dict:
    comments = fetch_comments(topic_id=topic_id, limit=500)
    counter = Counter()
    representative = []
    negative = []
    for comment in comments:
        if comment["sentiment"] == "negative":
            negative.append(comment["content"])
        if len(representative) < 5:
            representative.append(comment["content"])
        for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", comment["content"]):
            if len(token) >= 2:
                counter[token] += 1
    return {
        "top_keywords": [{"name": key, "value": value} for key, value in counter.most_common(10)],
        "representative_comments": representative,
        "negative_summary": "；".join(negative[:3]) if negative else "当前未见明显负面评论。",
    }
