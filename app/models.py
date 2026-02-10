from datetime import datetime
from pydantic import BaseModel, Field

class EphemeralKeyCreate(BaseModel):
    ttl_seconds: int = Field(..., ge=1, le=86400, description="Time to live in seconds (1-86400)")
    max_requests: int = Field(..., ge=1, le=10000, description="Maximum number of requests (1-10000)")

class EphemeralKeyResponse(BaseModel):
    key: str
    expire_at: datetime
    remaining: int

class EphemeralKeyStatus(BaseModel):
    key: str
    expire_at: datetime
    remaining: int

class ErrorResponse(BaseModel):
    error_code: str
    message: str
