from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["Demo"])

@router.get("/data")
def get_protected_data(request: Request):
    """
    A protected endpoint to demonstrate key usage.
    
    Requires a valid 'X-API-Key' header. Returns mock data and the
    remaining request count from the request state.
    """
    # Simulate usage
    request.state.usage = {
        "model": "gpt-3.5-turbo",
        "tokens": 150,
        "cost": 0.0003
    }
    
    return {
        "data": "This is protected data",
        "remaining_requests": request.state.remaining
    }
