from typing import Callable, Awaitable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from app.services.storage import get_storage

async def dispatch(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """
    Middleware to handle ephemeral key validation.
    
    Checks for 'X-API-Key' header, validates existence in storage,
    and manages request quotas.
    
    Args:
        request (Request): The incoming request.
        call_next (Callable): Function to process the next middleware or route.
        
    Returns:
        Response: The response from the next handler.
        
    Raises:
        HTTPException: If key is missing, invalid, expired, or quota exceeded.
    """
    # 1. Exclude paths
    # We exclude documentation, health check, and key management endpoints
    if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"] or \
       request.url.path.startswith("/api/keys/"):
        return await call_next(request)
    
    # 2. Extract X-API-Key
    api_key = request.headers.get("X-API-Key")
    if not api_key or not api_key.startswith("ephem_"):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error_code": "EPHEMERAL_KEY_INVALID",
                "message": "Key not found or expired"
            }
        )
    
    # 3. Check Storage existence
    storage = get_storage()
    if not storage.exists(api_key):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error_code": "EPHEMERAL_KEY_INVALID",
                "message": "Key not found or expired"
            }
        )
    
    # 4. Atomic Decr
    remaining = storage.decrement_remaining(api_key)
    
    # 5. Check if limit exceeded (remaining < 0)
    if remaining < 0:
        # Only cleanup if we are sure it's dead, but storage logic handles delete mostly.
        # Explicit delete is fine.
        storage.delete_key(api_key)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error_code": "EPHEMERAL_KEY_INVALID",
                "message": "Key expired or usage limit exceeded"
            }
        )
    
    # 6. Inject remaining count
    request.state.remaining = remaining
    return await call_next(request)
