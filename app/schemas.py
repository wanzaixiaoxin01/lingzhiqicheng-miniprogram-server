from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BannerOut(OrmModel):
    id: str
    title: str
    image_url: str
    link_type: str | None = None
    link_value: str | None = None
    sort_order: int
    status: str


class CampusOut(OrmModel):
    id: str
    name: str
    cover_url: str | None = None
    address: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    phone: str
    business_hours: str | None = None
    images: list[Any] | None = None
    intro: str | None = None
    status: str


class CourseOut(OrmModel):
    id: str
    title: str
    category: str
    cover_url: str | None = None
    summary: str | None = None
    suitable_grade: str | None = None
    service_period: str | None = None
    price: Decimal | None = None
    original_price: Decimal | None = None
    price_text: str | None = None
    tags: list[Any] | None = None
    content: str | None = None
    sort_order: int
    status: str


class ArticleOut(OrmModel):
    id: str
    type: str
    title: str
    cover_url: str | None = None
    summary: str | None = None
    content: str
    author: str | None = None
    sort_order: int
    status: str


class LeadOut(OrmModel):
    id: str
    name: str
    phone: str
    child_grade: str
    source: str
    campus_id: str | None = None
    course_id: str | None = None
    message: str | None = None
    follow_status: str
    follow_note: str | None = None
    created_at: datetime
