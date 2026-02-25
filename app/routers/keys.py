from fastapi import APIRouter, status, HTTPException
from app.models import EphemeralKeyCreate, EphemeralKeyResponse, EphemeralKeyStatus, ErrorResponse, IpPolicy, RPMRequest
from app.services.key_service import KeyService
from app.exceptions import KeyInvalidException

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

@router.put("/{key}/ip_policy", status_code=status.HTTP_200_OK, responses={404: {"model": ErrorResponse}})
def set_key_ip_policy(key: str, policy: IpPolicy):
    """
    Configure IP whitelist/blacklist policy for an ephemeral key.
    """
    try:
        KeyService.set_ip_policy(key, policy)
        return {"message": "Policy updated"}
    except KeyInvalidException:
        raise HTTPException(status_code=404, detail={
            "error_code": "KEY_NOT_FOUND",
            "message": "Key not found or expired"
        })

@router.put("/{key}/rpm", status_code=status.HTTP_200_OK, responses={404: {"model": ErrorResponse}})
def set_key_rpm(key: str, request: RPMRequest):
    """
    Configure RPM limit for an ephemeral key.
    """
    try:
        KeyService.set_rpm(key, request.rpm)
        return {"message": "RPM limit updated"}
    except KeyInvalidException:
        raise HTTPException(status_code=404, detail={
            "error_code": "KEY_NOT_FOUND",
            "message": "Key not found or expired"
        })

