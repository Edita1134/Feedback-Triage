
import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import os


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = None, period: int = None):
        super().__init__(app)
        # Default: 60 calls per 60 seconds (1 per second average)
        self.calls = calls or int(os.getenv("RATE_LIMIT_CALLS", 60))
        self.period = period or int(os.getenv("RATE_LIMIT_PERIOD", 60))
        
        # Store request timestamps for each IP
        self.requests = defaultdict(deque)
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check if this endpoint should be rate limited
        if self._should_rate_limit(request.url.path):
            if not self._is_allowed(client_ip):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {self.calls} requests per {self.period} seconds",
                        "status_code": 429,
                        "retry_after": self.period
                    }
                )
        
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the client IP address from the request"""
        # Check for forwarded IP first (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        return request.client.host if request.client else "unknown"
    
    def _should_rate_limit(self, path: str) -> bool:
        """Determine if a path should be rate limited"""
        # Rate limit the main triage endpoint and any API endpoints
        rate_limited_paths = ["/api/triage", "/api/dashboard"]
        return any(path.startswith(p) for p in rate_limited_paths)
    
    def _is_allowed(self, client_ip: str) -> bool:
        """Check if the client is allowed to make a request"""
        now = time.time()
        
        # Clean old requests (older than the period)
        while (self.requests[client_ip] and 
               now - self.requests[client_ip][0] > self.period):
            self.requests[client_ip].popleft()
        
        # Check if under the limit
        if len(self.requests[client_ip]) < self.calls:
            # Add current request
            self.requests[client_ip].append(now)
            return True
        
        return False
    
    def get_remaining_requests(self, client_ip: str) -> int:
        """Get the number of remaining requests for a client"""
        now = time.time()
        
        # Clean old requests
        while (self.requests[client_ip] and 
               now - self.requests[client_ip][0] > self.period):
            self.requests[client_ip].popleft()
        
        return max(0, self.calls - len(self.requests[client_ip]))
    
    def get_reset_time(self, client_ip: str) -> float:
        """Get the time when the rate limit resets for a client"""
        if not self.requests[client_ip]:
            return time.time()
        
        return self.requests[client_ip][0] + self.period
