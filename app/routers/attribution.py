from fastapi import APIRouter, Depends, Query, status
from app.services.storage import get_storage
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

router = APIRouter(prefix="/api/attribution", tags=["Attribution"])

class AttributionLog(BaseModel):
    request_id: str
    token_id: str
    model: str
    endpoint: str
    status_code: int
    latency_ms: float
    total_tokens: int
    inflight_concurrency: int
    created_at: float

class AttributionResponse(BaseModel):
    logs: List[AttributionLog]
    total_count: int
    page: int
    page_size: int

@router.get("/requests", response_model=AttributionResponse)
def get_attribution_requests(
    start: Optional[float] = None,
    end: Optional[float] = None,
    token_id: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    storage = get_storage()
    filters = {
        "start": start,
        "end": end,
        "token_id": token_id,
        "model": model,
        "status": status
    }
    
    # Filter out None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    logs, total = storage.get_attribution_logs(filters, page, page_size)
    
    return {
        "logs": logs,
        "total_count": total,
        "page": page,
        "page_size": page_size
    }