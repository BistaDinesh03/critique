import time
import ipaddress
from collections import OrderedDict
from threading import Lock
from fastapi import HTTPException, Request, Depends

_requests = OrderedDict()
_requests_lock = Lock()
_request_count = 0

# Sweeping every request would scan all clients. The cap also bounds memory
# when new addresses arrive faster than their windows expire; eviction may
# give the least recently seen client a fresh allowance if it returns.
SWEEP_INTERVAL = 100
MAX_TRACKED_KEYS = 10_000

RATE_LIMITS = {
    "auth": {"max_requests": 10, "window": 60},
    "project_create": {"max_requests": 5, "window": 300},
    "response_submit": {"max_requests": 10, "window": 300},
    "analytics": {"max_requests": 60, "window": 60},
    "project_delete": {"max_requests": 20, "window": 300},
    "email_login_start": {"max_requests": 3, "window": 900},
    "email_login_verify": {"max_requests": 10, "window": 60},
}


def _sweep_expired(now: float):
    for key, timestamps in list(_requests.items()):
        endpoint = key.split(":", 1)[0]
        window = RATE_LIMITS[endpoint]["window"]
        if not timestamps or now - timestamps[-1] >= window:
            del _requests[key]


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
        global _request_count
        config = RATE_LIMITS.get(endpoint)
        if not config:
            return

        client_ip = _client_ip(request)
        key = f"{endpoint}:{client_ip}"

        with _requests_lock:
            now = time.time()
            _request_count += 1
            if _request_count % SWEEP_INTERVAL == 0:
                _sweep_expired(now)

            timestamps = [ts for ts in _requests.get(key, ()) if now - ts < config["window"]]
            if key not in _requests and len(_requests) >= MAX_TRACKED_KEYS:
                _requests.popitem(last=False)
            _requests[key] = timestamps
            _requests.move_to_end(key)

            if len(timestamps) >= config["max_requests"]:
                raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

            timestamps.append(now)

    return dependency


def reset_rate_limits():
    global _request_count
    with _requests_lock:
        _requests.clear()
        _request_count = 0
