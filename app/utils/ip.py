import ipaddress
from typing import List
from fastapi import Request
from app.config import settings

def get_client_ip(request: Request) -> str:
    """
    Get client IP respecting trusted proxy configuration.
    If TRUSTED_PROXIES is configured, checks X-Forwarded-For.
    Otherwise returns direct connection IP.
    """
    trusted_proxies = [ip.strip() for ip in settings.TRUSTED_PROXIES.split(",") if ip.strip()]
    
    if not request.client:
        return "0.0.0.0"

    if not trusted_proxies:
        return request.client.host

    client_host = request.client.host
    
    # Check if direct client is a trusted proxy
    is_trusted = False
    try:
        if client_host:
            client_ip = ipaddress.ip_address(client_host)
            for proxy in trusted_proxies:
                if client_ip in ipaddress.ip_network(proxy):
                    is_trusted = True
                    break
    except ValueError:
        pass

    if is_trusted:
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            # X-Forwarded-For: <client>, <proxy1>, <proxy2>
            # We take the first one? Or strict parsing? 
            # Usually the Left-most is the original client.
            return x_forwarded_for.split(",")[0].strip()
            
    return client_host

def check_ip_allowed(client_ip: str, mode: str, ips: List[str]) -> bool:
    """
    Check if IP is allowed based on policy.
    """
    try:
        target_ip = ipaddress.ip_address(client_ip)
    except ValueError:
        # Invalid IP format from client? Reject or treat as not matching.
        return False

    matched = False
    for cidr in ips:
        try:
            if target_ip in ipaddress.ip_network(cidr.strip(), strict=False):
                matched = True
                break
        except ValueError:
            continue

    if mode == "whitelist":
        return matched
    elif mode == "blacklist":
        return not matched
    
    # Default to False (Deny) for unknown modes for safety,
    # though strict validation should prevent this.
    return False
