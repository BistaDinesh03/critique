import time
import ipaddress
from collections import defaultdict
from fastapi import HTTPException, Request, Depends

_requests = defaultdict(list)

RATE_LIMITS = {
    "auth": {"max_requests": 10, "window": 60},
    "project_create": {"max_requests": 5, "window": 300},
    "response_submit": {"max_requests": 10, "window": 300},
    "analytics": {"max_requests": 60, "window": 60},
    "project_delete": {"max_requests": 20, "window": 300},
}


def _cleanup_old(key: str, window: int):
    now = time.time()
    _requests[key] = [ts for ts in _requests[key] if now - ts < window]


def _client_ip(request: Request) -> str:
    """Return the best available client IP for rate-limit keying.

    Prefers the CF-Connecting-IP header, which Cloudflare sets on proxied
    requests and which clients cannot spoof. Falls back to the TCP peer IP.
    Does not read the forwarded-for header: Render appends to it rather than
    stripping it, so trusting it would allow rate-limit bypass by rotation.
    """
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        try:
            ipaddress.ip_address(cf_ip)
            return cf_ip
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


def rate_limit(endpoint: str):
    def dependency(request: Request):
        config = RATE_LIMITS.get(endpoint)
        if not config:
            return

        client_ip = _client_ip(request)
        key = f"{endpoint}:{client_ip}"

        _cleanup_old(key, config["window"])

        if len(_requests[key]) >= config["max_requests"]:
            raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

        _requests[key].append(time.time())

    return dependency


def reset_rate_limits():
    _requests.clear()
