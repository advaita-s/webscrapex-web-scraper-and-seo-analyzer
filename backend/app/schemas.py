from pydantic import BaseModel
from typing import Optional, Dict, Any

class ScrapeRequest(BaseModel):
    url: str
    selectors: Optional[Dict[str, str]] = None
    save_csv: Optional[bool] = False
    ai_summary: Optional[bool] = False

class ScrapeResponse(BaseModel):
    id: int
    status: str

class ResultResponse(BaseModel):
    id: int
    url: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
