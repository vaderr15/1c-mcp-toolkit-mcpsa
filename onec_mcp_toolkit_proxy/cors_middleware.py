"""
CORS Middleware for MCP endpoints.

This module provides ASGI middleware for handling Cross-Origin Resource Sharing (CORS)
for browser-based MCP clients like MCP SuperAssistant extension.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

from typing import List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class CorsMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware for MCP endpoints.
    
    Handles:
    - Preflight OPTIONS requests
    - CORS headers for all /mcp responses
    - Configurable allowed origins
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
    - 2.1: Adds CORS headers for all /mcp responses
    - 2.2: Handles preflight OPTIONS requests
    - 2.3: Allows required headers
    - 2.4: Allows required methods
    - 2.5: Uses configured origins list
    - 2.6: Supports wildcard mode
    """
    
    ALLOWED_METHODS = ["GET", "POST", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS = [
        "Accept",
        "Content-Type",
        "Mcp-Session-Id",
        "Mcp-Protocol-Version"
    ]
    MAX_AGE = "86400"  # 24 hours
    
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: Optional[List[str]] = None,
        allow_all_origins: bool = False
    ):
        """
        Initialize CORS middleware.
        
        Args:
            app: ASGI application
            allow_origins: List of allowed origins (None = use from config)
            allow_all_origins: Allow all origins (wildcard *)
        """
        super().__init__(app)
        self.allow_origins = allow_origins or []
        self.allow_all_origins = allow_all_origins
        
        if self.allow_all_origins:
            logger.info("CORS: Allowing all origins (*)")
        elif self.allow_origins:
            logger.info(f"CORS: Allowing origins: {', '.join(self.allow_origins)}")
        else:
            logger.warning("CORS: No origins configured, CORS headers will not be added")
    
    def _should_add_cors(self, path: str) -> bool:
        """Check if CORS headers should be added for this path."""
        return path.startswith("/mcp") or path.startswith("/sse")
    
    def _is_browser_extension(self, origin: Optional[str]) -> bool:
        """Check if origin is from a browser extension."""
        if not origin:
            return False
        return origin.startswith("chrome-extension://") or origin.startswith("moz-extension://")
    
    def _get_allowed_origin(self, request_origin: Optional[str]) -> Optional[str]:
        """
        Determine the allowed origin for the response.
        
        Returns:
            - "*" if allow_all_origins is True
            - request_origin if it's in allow_origins list
            - request_origin if it's a browser extension (chrome-extension:// or moz-extension://)
            - None if origin is not allowed
        """
        if self.allow_all_origins:
            return "*"
        
        # Always allow browser extensions when CORS is configured
        if self._is_browser_extension(request_origin):
            return request_origin
        
        if request_origin and request_origin in self.allow_origins:
            return request_origin
        
        return None
    
    def _add_cors_headers(self, response: Response, allowed_origin: str) -> None:
        """Add CORS headers to response."""
        response.headers["Access-Control-Allow-Origin"] = allowed_origin
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.ALLOWED_METHODS)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.ALLOWED_HEADERS)
        response.headers["Access-Control-Max-Age"] = self.MAX_AGE
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add CORS headers if needed."""
        # Check if this is an MCP endpoint
        if not self._should_add_cors(request.url.path):
            return await call_next(request)
        
        # Get request origin
        request_origin = request.headers.get("origin")
        
        # Determine allowed origin
        allowed_origin = self._get_allowed_origin(request_origin)
        
        # Handle preflight OPTIONS request
        if request.method == "OPTIONS":
            logger.debug(f"CORS preflight request from origin: {request_origin}")
            
            if allowed_origin:
                response = Response(status_code=204)
                self._add_cors_headers(response, allowed_origin)
                logger.debug(f"CORS preflight approved for origin: {request_origin}")
                return response
            else:
                logger.warning(f"CORS preflight rejected for origin: {request_origin}")
                return Response(status_code=403, content="Origin not allowed")
        
        # Process actual request
        response = await call_next(request)
        
        # Add CORS headers to response
        if allowed_origin:
            self._add_cors_headers(response, allowed_origin)
            logger.debug(f"CORS headers added for origin: {request_origin}")
        
        return response
