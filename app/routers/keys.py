from fastapi import APIRouter, status
from app.models import EphemeralKeyCreate, EphemeralKeyResponse, EphemeralKeyStatus, ErrorResponse
from app.services.key_service import KeyService

router = APIRouter(prefix="/api/keys", tags=["Keys"])

@router.post("/ephemeral", response_model=EphemeralKeyResponse, status_code=status.HTTP_201_CREATED)
def create_ephemeral_key(data: EphemeralKeyCreate):
    """
    Create a new ephemeral API key.
    
    Accepts TTL and max requests parameters. Returns the generated key
    and its expiration time.
    """
    return KeyService.create_key(data)

@router.get("/{key}", response_model=EphemeralKeyStatus, responses={404: {"model": ErrorResponse}})
def get_key_status(key: str):
    """
    Get the status of a specific ephemeral key.
    
    Returns standard info including remaining requests and expiration time.
    Raises 404 if the key does not exist or has expired.
    """
    return KeyService.get_key_status(key)
