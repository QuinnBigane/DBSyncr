"""
Rate Limiting Service for DBSyncr
Implements request throttling and rate limiting using slowapi.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from utils.logging_config import get_logger


class RateLimitService:
    """Service for handling rate limiting and request throttling."""

    def __init__(self):
        self.logger = get_logger("RateLimitService")

        # Create rate limiter with different limits for different endpoints
        self.limiter = Limiter(key_func=get_remote_address)

        # Rate limit configurations
        self.default_limit = "100/minute"  # General API limit
        self.auth_limit = "10/minute"      # Authentication endpoints
        self.upload_limit = "5/minute"     # File upload endpoints
        self.admin_limit = "1000/minute"   # Admin endpoints (higher limit)

    def get_limiter(self):
        """Get the rate limiter instance."""
        return self.limiter

    def create_middleware(self):
        """Create SlowAPI middleware for FastAPI."""
        return SlowAPIMiddleware

    def handle_rate_limit_exceeded(self, request: Request, exc: RateLimitExceeded):
        """Handle rate limit exceeded exceptions."""
        self.logger.warning(f"Rate limit exceeded for {request.client.host}: {exc.detail}")

        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "message": "Rate limit exceeded. Please try again later.",
                "retry_after": exc.retry_after,
                "limit": exc.limit,
                "remaining": 0
            },
            headers={
                "Retry-After": str(exc.retry_after),
                "X-RateLimit-Limit": str(exc.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(exc.reset_time)
            }
        )

    @staticmethod
    def get_endpoint_limit(endpoint: str) -> str:
        """Get appropriate rate limit for an endpoint."""
        # Authentication endpoints
        if any(path in endpoint for path in ["/auth/login", "/auth/signup", "/auth/refresh"]):
            return "10/minute"

        # File upload endpoints
        if any(path in endpoint for path in ["/upload", "/export"]):
            return "5/minute"

        # Admin endpoints
        if endpoint.startswith("/admin"):
            return "1000/minute"

        # Health check (higher limit)
        if endpoint == "/health":
            return "1000/minute"

        # Default limit
        return "100/minute"