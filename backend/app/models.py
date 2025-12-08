# app/models.py
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON  # fallback for sqlite
from sqlalchemy import JSON as SA_JSON
from typing import Optional
from datetime import datetime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

# Use SA_JSON where available; for sqlite dialect we can also import sqlite JSON type.
# We'll prefer SA_JSON but fall back to sqlite dialect JSON if needed.
JSON_TYPE = None
try:
    JSON_TYPE = SA_JSON
except Exception:
    JSON_TYPE = SQLITE_JSON

class ScrapeJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    selectors: Optional[str] = None
    status: str = "pending"
    # Use plain `dict` for pydantic, and tell SQLModel to use a JSON column in DB
    result: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON_TYPE)  # maps to proper JSON type or text-backed JSON on SQLite
    )
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None

class ScrapeResult(Base):
    __tablename__ = "scrape_results"
    id = Column(Integer, primary_key=True)
    job_id = Column(String, index=True, unique=True)
    url = Column(String)
    data = Column(JSON)           # existing
    ai_summary = Column(String)   # existing
    # NEW:
    price = Column(Float, nullable=True)
    currency = Column(String(8), nullable=True)

    # relation for price history
    price_history = relationship("PriceHistory", back_populates="result")


class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True)
    result_id = Column(Integer, ForeignKey("scrape_results.id"))
    price = Column(Float)
    currency = Column(String(8))
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    result = relationship("ScrapeResult", back_populates="price_history")