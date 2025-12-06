"""Rate limiting configuration for the API."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global rate limiter instance
# Default: 100 requests per minute per IP
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
