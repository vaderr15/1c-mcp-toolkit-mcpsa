"""
SSE Event Formatter for SuperAssistant compatibility.

This module provides formatting of SSE events in the format expected by
the SuperAssistant browser extension. The key difference from legacy SSE
is using 'message' event type for JSON-RPC responses (not 'data').

SuperAssistant extension specifically listens for 'message' events for JSON-RPC,
while 'data' events are ignored. This is the opposite of what was initially expected.

Validates: Requirements 3.4
"""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SseEventFormatter:
    """
    Formats SSE events for SuperAssistant compatibility.
    
    The SuperAssistant browser extension expects SSE events in a specific format:
    - Endpoint event: event type 'endpoint', data contains POST URL
    - Response events: event type 'message' (NOT 'data'), data contains JSON-RPC message
    
    This differs from what was initially expected - SuperAssistant uses 'message' events.
    """
    
    @staticmethod
    def format_endpoint_event(post_url: str) -> Dict[str, str]:
        """
        Format endpoint event for SuperAssistant.
        
        The endpoint event tells the client where to POST messages.
        It includes the session_id in the URL query parameters.
        
        Args:
            post_url: Full POST URL with session_id (e.g., "/sse/message?session_id=xxx")
            
        Returns:
            Dictionary with 'event' and 'data' keys for SSE transmission
            
        Example:
            >>> SseEventFormatter.format_endpoint_event("/sse/message?session_id=abc123")
            {'event': 'endpoint', 'data': '/sse/message?session_id=abc123'}
            
        Validates: Requirements 3.4 - SSE event format compatible with SuperAssistant
        """
        return {
            "event": "endpoint",
            "data": post_url
        }
    
    @staticmethod
    def format_data_event(message: Dict[str, Any]) -> Dict[str, str]:
        """
        Format data event with JSON-RPC message for SuperAssistant.
        
        IMPORTANT: Uses 'message' event type, NOT 'data' event type.
        SuperAssistant actually expects 'message' events for JSON-RPC responses.
        
        Args:
            message: JSON-RPC message dictionary (request or response)
            
        Returns:
            Dictionary with 'event' and 'data' keys for SSE transmission
            
        Example:
            >>> msg = {"jsonrpc": "2.0", "id": 1, "result": {"status": "ok"}}
            >>> SseEventFormatter.format_data_event(msg)
            {'event': 'message', 'data': '{"jsonrpc":"2.0","id":1,"result":{"status":"ok"}}'}
            
        Validates: Requirements 3.4 - Use 'message' events for JSON-RPC responses
        """
        # Serialize message to JSON string
        # Use ensure_ascii=False to support Cyrillic characters in 1C responses
        message_json = json.dumps(message, ensure_ascii=False, separators=(',', ':'))
        
        return {
            "event": "message",
            "data": message_json
        }
