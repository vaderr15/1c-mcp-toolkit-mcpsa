"""
Streamable HTTP Client for SuperAssistant SSE Bridge.

This module provides an internal HTTP client for communicating with the
Streamable HTTP transport. It handles session creation, message sending,
and session cleanup for the bridge component.

Validates: Requirements 3.1, 3.2, 3.6
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, Optional, Tuple
import uuid

import httpx

logger = logging.getLogger(__name__)


class StreamableHttpClient:
    """
    Internal client for Streamable HTTP transport.
    
    This client handles internal communication with the Streamable HTTP transport
    on behalf of the SuperAssistant SSE bridge. It creates sessions, sends messages,
    and handles cleanup using the MCP Streamable HTTP protocol.
    
    The client makes HTTP requests to the same server (localhost) to communicate
    with the existing Streamable HTTP transport implementation.
    
    Validates: Requirements 3.1, 3.2, 3.6
    - 3.1: Create internal Streamable HTTP sessions
    - 3.2: Send messages to Streamable HTTP transport
    - 3.6: Delete sessions for cleanup
    """
    
    def __init__(self, base_url: str = "http://localhost:6003"):
        """
        Initialize client with base URL for internal requests.
        
        Args:
            base_url: Base URL for internal HTTP requests to the MCP server
                     (default: http://localhost:6003)
        """
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        logger.debug(f"StreamableHttpClient initialized with base_url: {self.base_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client instance."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),  # 30 second timeout
                follow_redirects=True
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("StreamableHttpClient closed")
    
    async def create_session(
        self, 
        channel: str
    ) -> Tuple[str, AsyncIterator[bytes]]:
        """
        Create new Streamable HTTP session.
        
        Creates a Streamable HTTP session using the proper protocol:
        1. First sends an initialize message via POST to create the session
        2. Then connects via GET with SSE to receive responses
        
        Args:
            channel: Channel ID for isolation (will be passed as query parameter)
            
        Returns:
            Tuple of (session_id, response_stream) where:
            - session_id: The MCP session ID returned by the server
            - response_stream: Async iterator of response bytes from the session
            
        Raises:
            httpx.HTTPError: If the HTTP request fails
            ValueError: If the server response is invalid
            
        Validates: Requirements 3.1
        - 3.1: Create internal Streamable HTTP session for SSE connection
        """
        # Generate a unique session ID for this Streamable HTTP session
        session_id = str(uuid.uuid4())
        
        # Prepare URL with channel parameter
        url = f"{self.base_url}/mcp"
        params = {"channel": channel} if channel != "default" else {}
        
        client = await self._get_client()
        
        try:
            logger.debug(
                f"Creating Streamable HTTP session {session_id[:8]}... "
                f"for channel '{channel}'"
            )
            
            # Step 1: Initialize session with POST request
            init_headers = {
                "Content-Type": "application/json",
                "mcp-session-id": session_id,
                "mcp-protocol-version": "2024-11-05",
            }
            
            # Send initialize message to create the session
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "superassistant-sse-bridge",
                        "version": "1.0.0"
                    }
                }
            }
            
            logger.debug(f"Initializing session {session_id[:8]}... with POST")
            init_response = await client.post(url, headers=init_headers, params=params, json=init_message)
            init_response.raise_for_status()
            
            # Step 2: Connect via GET with SSE to receive responses
            sse_headers = {
                "Accept": "text/event-stream",
                "mcp-session-id": session_id,
                "mcp-protocol-version": "2024-11-05",
                "Cache-Control": "no-cache",
            }
            
            logger.debug(f"Connecting to SSE stream for session {session_id[:8]}...")
            response = await client.get(url, headers=sse_headers, params=params)
            response.raise_for_status()
            
            # Verify response is SSE
            content_type = response.headers.get("content-type", "")
            if "text/event-stream" not in content_type:
                raise ValueError(
                    f"Expected SSE response, got content-type: {content_type}"
                )
            
            logger.info(
                f"Streamable HTTP session created: {session_id[:8]}... "
                f"for channel '{channel}'"
            )
            
            # Return session ID and response stream
            return session_id, self._stream_response(response)
            
        except httpx.HTTPError as e:
            logger.error(
                f"Failed to create Streamable HTTP session {session_id[:8]}...: {e}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error creating session {session_id[:8]}...: {e}"
            )
            raise
    
    async def _stream_response(self, response: httpx.Response) -> AsyncIterator[bytes]:
        """
        Stream response bytes from HTTP response.
        
        Args:
            response: The HTTP response to stream
            
        Yields:
            Bytes from the response stream
        """
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        except Exception as e:
            logger.warning(f"Error streaming response: {e}")
            raise
    
    async def send_message(
        self, 
        session_id: str, 
        message: Dict,
        channel: str = "default"
    ) -> Dict:
        """
        Send message to Streamable HTTP session.
        
        Makes an internal POST request to the /mcp endpoint with the JSON-RPC
        message and proper MCP headers. The message will be processed by the
        MCP server and the response returned.
        
        Args:
            session_id: The MCP session ID for the target session
            message: JSON-RPC message to send (dict format)
            channel: Channel ID for routing (default: "default")
            
        Returns:
            JSON-RPC response as a dictionary
            
        Raises:
            httpx.HTTPError: If the HTTP request fails
            ValueError: If the response is not valid JSON
            
        Validates: Requirements 3.2
        - 3.2: Forward messages to Streamable HTTP transport
        """
        # Prepare headers for Streamable HTTP protocol
        headers = {
            "Content-Type": "application/json",
            "mcp-session-id": session_id,
            "mcp-protocol-version": "2024-11-05",
        }
        
        # Prepare URL with channel parameter
        url = f"{self.base_url}/mcp"
        params = {"channel": channel} if channel != "default" else {}
        
        client = await self._get_client()
        
        try:
            logger.debug(
                f"Sending message to session {session_id[:8]}... "
                f"on channel '{channel}': {message.get('method', 'unknown')}"
            )
            
            # Make POST request with JSON message
            response = await client.post(
                url, 
                headers=headers, 
                params=params,
                json=message
            )
            response.raise_for_status()
            
            # Parse JSON response
            response_data = response.json()
            
            logger.debug(
                f"Received response from session {session_id[:8]}...: "
                f"{response_data.get('result', {}).get('method', 'unknown') if 'result' in response_data else 'error'}"
            )
            
            return response_data
            
        except httpx.HTTPError as e:
            logger.error(
                f"Failed to send message to session {session_id[:8]}...: {e}"
            )
            raise
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                f"Invalid JSON response from session {session_id[:8]}...: {e}"
            )
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error sending message to session {session_id[:8]}...: {e}"
            )
            raise
    
    async def delete_session(self, session_id: str, channel: str = "default") -> None:
        """
        Delete Streamable HTTP session.
        
        Makes an internal DELETE request to clean up the Streamable HTTP session.
        This should be called when the corresponding SSE connection is closed
        to prevent resource leaks.
        
        Args:
            session_id: The MCP session ID to delete
            channel: Channel ID for routing (default: "default")
            
        Raises:
            httpx.HTTPError: If the HTTP request fails (non-404 errors)
            
        Note:
            404 errors are ignored as the session may have already been cleaned up.
            
        Validates: Requirements 3.6
        - 3.6: Clean up Streamable HTTP session when SSE disconnects
        """
        # Prepare headers for Streamable HTTP protocol
        headers = {
            "mcp-session-id": session_id,
            "mcp-protocol-version": "2024-11-05",
        }
        
        # Prepare URL with channel parameter
        url = f"{self.base_url}/mcp"
        params = {"channel": channel} if channel != "default" else {}
        
        client = await self._get_client()
        
        try:
            logger.debug(
                f"Deleting Streamable HTTP session {session_id[:8]}... "
                f"on channel '{channel}'"
            )
            
            # Make DELETE request to clean up session
            response = await client.delete(url, headers=headers, params=params)
            
            # Ignore 404 errors (session already cleaned up)
            if response.status_code == 404:
                logger.debug(
                    f"Session {session_id[:8]}... already deleted (404)"
                )
                return
            
            response.raise_for_status()
            
            logger.info(
                f"Streamable HTTP session deleted: {session_id[:8]}... "
                f"from channel '{channel}'"
            )
            
        except httpx.HTTPError as e:
            # Don't raise for 404 errors
            if hasattr(e, 'response') and e.response.status_code == 404:
                logger.debug(
                    f"Session {session_id[:8]}... not found during deletion (expected)"
                )
                return
            
            logger.error(
                f"Failed to delete session {session_id[:8]}...: {e}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error deleting session {session_id[:8]}...: {e}"
            )
            raise


# Global instance for use by the bridge
streamable_http_client = StreamableHttpClient()