from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TopicCreate(BaseModel):
    name: str
    keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    enabled: bool = True


class TopicUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[list[str]] = None
    exclude_keywords: Optional[list[str]] = None
    enabled: Optional[bool] = None


class TopicOut(BaseModel):
    id: int
    name: str
    keywords: list[str]
    exclude_keywords: list[str]
    enabled: bool
    created_at: datetime


class PostOut(BaseModel):
    id: int
    topic_id: int
    platform: str
    source_id: str
    title: str
    summary: str
    author: str
    published_at: datetime
    likes: int
    shares: int
    comments_count: int
    url: str
    sentiment: str
    created_at: datetime


class CommentOut(BaseModel):
    id: int
    post_id: int
    content: str
    published_at: datetime
    sentiment: str
    created_at: datetime


class AlertOut(BaseModel):
    id: int
    topic_id: int
    alert_type: str
    level: str
    reason: str
    status: str
    created_at: datetime


class DashboardResponse(BaseModel):
    topic: TopicOut
    total_posts: int
    total_comments: int
    total_likes: int
    total_shares: int
    negative_rate: float
    alert_count: int
    platform_distribution: list[dict[str, Any]]
    sentiment_distribution: list[dict[str, Any]]


class TrendPoint(BaseModel):
    bucket: str
    platform: str
    posts: int
    likes: int
    shares: int
    comments: int
    negative_posts: int


class CommentInsightResponse(BaseModel):
    top_keywords: list[dict[str, Any]]
    representative_comments: list[str]
    negative_summary: str


class CollectResponse(BaseModel):
    inserted_posts: int
    inserted_comments: int
    alerts_created: int
    sampled_topics: list[int]
