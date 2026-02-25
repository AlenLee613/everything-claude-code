from typing import Callable, Awaitable, Optional, Tuple
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from app.services.storage import get_storage
from app.utils.ip import get_client_ip, check_ip_allowed
from app.exceptions import KeyInvalidException
from loguru import logger
import json
import uuid
import time
import asyncio

# Global concurrency counter
active_requests = 0

async def dispatch(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """
    Middleware to handle ephemeral key validation and logging.
    """
    global active_requests
    
    # Track Request Start
    active_requests += 1
    inflight_at_start = active_requests
    start_time = time.time()
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    path = request.url.path
    client_ip = get_client_ip(request)
    
    # Initialize default log data
    model = "unknown"
    token_id = "unknown"
    total_tokens = 0
    status_code = 500 # Default to error if crash
    endpoint = f"{request.method} {path}"

    try:
        # 1. Exclude Utility paths from auth
        if path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            response = await call_next(request)
            status_code = response.status_code
            return response

        # 2. Exclude Usage Export and Attribution
        if path.startswith("/api/usage/export") or path.startswith("/api/attribution"):
            response = await call_next(request)
            status_code = response.status_code
            return response
            
        logger.info(f"Incoming Request: {request.method} {path} | IP: {client_ip}")

        # 3. Key Creation is Public
        if path == "/api/keys/ephemeral" and request.method == "POST":
            response = await call_next(request)
            status_code = response.status_code
            return response

        # 4. Determine Key (token_id)
        api_key = request.headers.get("X-API-Key")
        if not api_key and path.startswith("/api/keys/"):
            parts = path.split("/")
            if len(parts) >= 4 and parts[3].startswith("ephem_"):
                api_key = parts[3]
        
        if api_key:
            token_id = api_key

        # 5. Auth Logic
        result = await _check_auth(request, api_key, client_ip)
        if isinstance(result, Response):
             status_code = result.status_code
             return result
        
        # Auth passed
        response = await call_next(request)
        status_code = response.status_code
        
        # Extract metadata from response or state
        if hasattr(request.state, "usage"):
            usage = request.state.usage
            model = usage.get("model", model)
            total_tokens = usage.get("tokens", total_tokens)
            
            # Log standard usage (CSV)
            if response.status_code < 400:
                try:
                    storage = get_storage()
                    usage_record = {
                        "timestamp": start_time,
                        "model": model,
                        "tokens": total_tokens,
                        "cost": usage.get("cost", 0.0)
                    }
                    storage.log_usage(token_id, usage_record)
                except Exception as e:
                    logger.error(f"Failed to log usage: {e}")
            
        return response

    except Exception as e:
        status_code = 500
        logger.error(f"Request failed: {e}")
        raise e
    finally:
        active_requests -= 1
        duration = (time.time() - start_time) * 1000
        
        # Log Attribution
        if path not in ["/health", "/docs", "/openapi.json", "/redoc"] and not path.startswith("/api/usage") and not path.startswith("/api/attribution"):
             try:
                 storage = get_storage()
                 log_entry = {
                     "request_id": request_id,
                     "token_id": token_id,
                     "model": model,
                     "endpoint": endpoint,
                     "status_code": status_code,
                     "latency_ms": duration,
                     "total_tokens": total_tokens,
                     "inflight_concurrency": inflight_at_start,
                     "created_at": start_time
                 }
                 storage.log_attribution(log_entry)
             except Exception as e:
                 logger.error(f"Failed to log attribution: {e}")

async def _check_auth(request: Request, api_key: Optional[str], client_ip: str) -> Optional[Response]:
    """
    Performs authentication and rate limiting checks.
    Returns Response if auth failed, None if passed.
    """
    path = request.url.path
    storage = get_storage()

    if not api_key:
        if path.startswith("/api/keys/"):
             return None
        
        logger.warning(f"Access Denied: Missing Key | IP: {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error_code": "EPHEMERAL_KEY_INVALID",
                "message": "Key not found or expired"
            }
        )
    
    if not api_key.startswith("ephem_"):
         logger.warning(f"Access Denied: Invalid Key Format {api_key} | IP: {client_ip}")
         return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error_code": "EPHEMERAL_KEY_INVALID",
                "message": "Key not found or expired"
            }
        )

    # Check Storage existence & Get Info
    status_info = storage.get_key_status(api_key)
    
    if not status_info:
        logger.warning(f"Access Denied: Key Not Found/Expired {api_key} | IP: {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error_code": "EPHEMERAL_KEY_INVALID",
                "message": "Key not found or expired"
            }
        )
    
    info_dict, _ = status_info
    
    # Check IP Policy
    ip_policy = None
    if "ip_policy" in info_dict:
        try:
            val = info_dict["ip_policy"]
            if isinstance(val, str):
                ip_policy = json.loads(val)
            else:
                ip_policy = val
        except Exception as e:
            logger.error(f"Failed to parse IP policy for key {api_key}: {e}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={ 
                    "error_code": "POLICY_ERROR", 
                    "message": "Invalid policy configuration"
                }
            )
            
    if ip_policy:
        if not check_ip_allowed(client_ip, ip_policy.get("mode"), ip_policy.get("ips", [])):
            logger.warning(f"Access denied for IP {client_ip} by policy for key {api_key}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error_code": "IP_NOT_ALLOWED",
                    "message": "Access denied by IP policy"
                }
            )

    # Rate Limiting
    is_management_action = path.startswith("/api/keys/")
    
    if not is_management_action:
        # Check RPM limit if configured
        if "rpm" in info_dict:
            try:
                rpm_limit = int(info_dict["rpm"])
                if rpm_limit > 0:
                    if not storage.check_rate_limit(api_key, rpm_limit):
                        logger.warning(f"Rate Limit Exceeded: Key {api_key} (Limit: {rpm_limit} RPM) | IP: {client_ip}")
                        return JSONResponse(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            content={
                                "error_code": "RATE_LIMIT_EXCEEDED",
                                "message": "Rate limit exceeded"
                            }
                        )
            except (ValueError, TypeError):
                logger.error(f"Invalid RPM configuration for key {api_key}: {info_dict['rpm']}")

        remaining = storage.decrement_remaining(api_key)
        
        if remaining < 0:
            storage.delete_key(api_key)
            logger.warning(f"Access Denied: Key {api_key} usage limit exceeded | IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error_code": "EPHEMERAL_KEY_INVALID",
                    "message": "Key expired or usage limit exceeded"
                }
            )
        request.state.remaining = remaining
    else:
        request.state.remaining = status_info[1]
        
    return None
