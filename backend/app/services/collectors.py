from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import md5
import random

from ..storage import fetch_comments, insert_comment, insert_post, get_topic, now_iso
from .analytics import classify_sentiment, update_metrics_for_topic


PLATFORMS = ("weibo", "wechat")


@dataclass
class SimulatedPost:
    platform: str
    source_id: str
    title: str
    summary: str
    author: str
    published_at: str
    likes: int
    shares: int
    comments_count: int
    url: str
    sentiment: str
    comments: list[str]


def _topic_seed(topic_id: int, platform: str, index: int) -> int:
    digest = md5(f"{topic_id}:{platform}:{index}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _build_post(topic: dict, platform: str, index: int) -> SimulatedPost:
    seed = _topic_seed(topic["id"], platform, index)
    rng = random.Random(seed)
    keyword = topic["keywords"][index % len(topic["keywords"])] if topic["keywords"] else topic["name"]
    tone = rng.choice(["积极", "中性", "负面"])
    title = f"{topic['name']}相关动态：{keyword} 第{index + 1}条"
    summary = f"围绕{keyword}的最新讨论，内容情绪偏{tone}，涉及群众反馈、办理进展和传播扩散。"
    published_at = datetime.now(timezone.utc) - timedelta(minutes=rng.randint(0, 90))
    likes = rng.randint(15, 480)
    shares = rng.randint(2, 120)
    comments_count = rng.randint(3, 80)
    comments = [
        f"这个话题里关于{keyword}的讨论值得关注。",
        f"希望相关部门尽快回应{keyword}反馈。",
        f"从评论看，大家对{keyword}的关注度很高。",
    ]
    if tone == "负面":
        comments.append(f"对于{keyword}的处理速度有些担心。")
    return SimulatedPost(
        platform=platform,
        source_id=f"{platform}-{topic['id']}-{index}",
        title=title,
        summary=summary,
        author=f"{platform}_account_{index + 1}",
        published_at=published_at.isoformat(),
        likes=likes,
        shares=shares,
        comments_count=comments_count,
        url=f"https://example.com/{platform}/{topic['id']}/{index}",
        sentiment=classify_sentiment(title + summary + " ".join(comments)),
        comments=comments,
    )


def collect_for_topic(topic_id: int, source: str = "manual") -> dict[str, int]:
    topic = get_topic(topic_id)
    if not topic or not topic["enabled"]:
        return {"inserted_posts": 0, "inserted_comments": 0, "alerts_created": 0}

    inserted_posts = 0
    inserted_comments = 0
    alerts_created = 0

    for platform in PLATFORMS:
        for index in range(3):
            post = _build_post(topic, platform, index)
            if topic["exclude_keywords"] and any(ex in post.title for ex in topic["exclude_keywords"]):
                continue
            post_id = insert_post(
                {
                    "topic_id": topic_id,
                    "platform": post.platform,
                    "source_id": post.source_id,
                    "title": post.title,
                    "summary": post.summary,
                    "author": post.author,
                    "published_at": post.published_at,
                    "likes": post.likes,
                    "shares": post.shares,
                    "comments_count": post.comments_count,
                    "url": post.url,
                    "sentiment": post.sentiment,
                    "created_at": now_iso(),
                }
            )
            if post_id is None:
                continue
            inserted_posts += 1
            for item in post.comments:
                comment_sentiment = classify_sentiment(item)
                insert_comment(post_id, item, post.published_at, comment_sentiment)
                inserted_comments += 1

    alerts_created += update_metrics_for_topic(topic_id)
    return {
        "inserted_posts": inserted_posts,
        "inserted_comments": inserted_comments,
        "alerts_created": alerts_created,
    }
