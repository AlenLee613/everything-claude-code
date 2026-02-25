from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import sys

from app.routers import keys, demo
from app.routers.usage import router as usage_router
from app.routers.attribution import router as attribution_router
from app.middleware.auth import dispatch

# Configure Loguru for JSON logging
logger.remove()
logger.add(sys.stderr, format="{message}", serialize=True, level="INFO")
logger.add("logs/app.log", rotation="10 MB", retention="10 days", level="INFO", serialize=True)

app = FastAPI(title="Ephemeral Key API")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error_code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# Register middleware
app.add_middleware(BaseHTTPMiddleware, dispatch=dispatch)

# Include routers
app.include_router(keys.router)
app.include_router(demo.router)
app.include_router(usage_router)
app.include_router(attribution_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
