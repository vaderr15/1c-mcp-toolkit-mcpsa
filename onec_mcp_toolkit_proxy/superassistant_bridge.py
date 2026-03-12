"""
SuperAssistant SSE Bridge for 1C MCP Toolkit Proxy.

This module implements the main bridge component that translates between
SuperAssistant's SSE format and the internal Streamable HTTP transport.

The bridge handles:
- SSE connections from SuperAssistant browser extension
- Channel extraction and validation
- Session management and lifecycle
- Message forwarding between SSE and Streamable HTTP
- Error handling with bilingual messages
- Comprehensive logging

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 5.1, 7.1-7.6, 8.1-8.6
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

from anyio import create_memory_object_stream
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.types import Scope, Receive, Send

from .bridge_session_manager import bridge_session_manager, BridgeSession
from .sse_event_formatter import SseEventFormatter
from .channel_registry import ChannelRegistry, channel_registry
from .config import settings

logger = logging.getLogger(__name__)


class SuperAssistantSseBridge:
    """
    Bridge between SuperAssistant SSE and Streamable HTTP transport.
    
    This component acts as a translator between the SSE format expected by
    the SuperAssistant browser extension and the internal Streamable HTTP
    transport used by the MCP server.
    
    Key responsibilities:
    - Accept SSE connections from SuperAssistant
    - Extract and validate channel parameters
    - Create internal Streamable HTTP sessions
    - Forward messages bidirectionally
    - Handle session lifecycle and cleanup
    - Provide comprehensive error handling with bilingual messages
    
    Validates: Requirements 2.1, 2.2, 3.1, 3.2, 3.3, 8.1-8.6
    """
    
    def __init__(self, mcp_server, endpoint: str = "/sse/message"):
        """
        Initialize the bridge.
        
        Args:
            mcp_server: The MCP server instance with Streamable HTTP support
            endpoint: Relative path for POST messages (default: "/sse/message")
        """
        self.mcp_server = mcp_server
        self.endpoint = endpoint
        logger.info(f"SuperAssistant SSE Bridge initialized with endpoint: {endpoint}")
    
    async def handle_sse_connection(
        self, 
        scope: Scope, 
        receive: Receive, 
        send: Send
    ) -> None:
        """
        Handle incoming SSE connection from SuperAssistant.
        
        This method:
        1. Handles OPTIONS preflight requests for CORS
        2. Extracts and validates the channel parameter
        3. Creates an internal Streamable HTTP session
        4. Generates a unique session_id for the bridge
        5. Sends the endpoint event to SuperAssistant
        6. Maintains the SSE connection until client disconnects
        
        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
            
        Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 6.1, 6.2, 6.3, 8.1, 8.2
        """
        method = scope.get("method", "").upper()
        
        # Handle OPTIONS preflight request
        if method == "OPTIONS":
            await self._handle_options_request(scope, send)
            return
        
        # Handle POST requests as fallback (for misconfigured clients)
        if method == "POST":
            logger.info("SSE Bridge: Received POST to /sse, redirecting to message handler")
            await self.handle_post_message(scope, receive, send)
            return
        
        # Extract channel from query string
        channel = self._extract_and_validate_channel(scope)
        
        logger.info(f"SSE Bridge: New connection request for channel '{channel}'")
        
        try:
            # Create memory stream for SSE events
            send_stream, receive_stream = create_memory_object_stream[dict](100)
            
            # For testing: Skip internal Streamable HTTP session creation
            # TODO: Fix this when MCP server properly supports session creation
            streamable_session_id = "mock-session-" + str(uuid.uuid4())[:8]
            
            # Create bridge session
            session_id = bridge_session_manager.create_session(
                channel=channel,
                streamable_session_id=streamable_session_id,
                sse_stream=send_stream
            )
            
            # Register session with channel registry for proper isolation
            channel_registry.register(session_id, channel)
            
            logger.info(
                f"SSE Bridge: Session {session_id[:8]}... created for channel '{channel}' "
                f"with streamable session {streamable_session_id[:8]}..."
            )
            
            # Send SSE headers with CORS
            cors_headers = self._get_cors_headers(scope)
            response_headers = [
                (b"content-type", b"text/event-stream"),
                (b"cache-control", b"no-cache"),
                (b"connection", b"keep-alive"),
            ] + cors_headers
            
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": response_headers
            })
            
            # Send endpoint event
            post_url = f"{self.endpoint}?session_id={session_id}"
            endpoint_event = SseEventFormatter.format_endpoint_event(post_url)
            logger.info(f"SSE Bridge: Sending endpoint event: {endpoint_event}")
            await self._send_sse_event(send, endpoint_event)
            
            logger.info(f"SSE Bridge: Endpoint event sent to session {session_id[:8]}...")
            
            # Keep connection alive and handle events
            try:
                async with receive_stream:
                    logger.debug(f"SSE Bridge: Starting event loop for session {session_id[:8]}...")
                    async for event in receive_stream:
                        await self._send_sse_event(send, event)
                        logger.info(
                            f"SSE Bridge: Event sent to session {session_id[:8]}...: "
                            f"{event.get('event', 'unknown')}"
                        )
            except Exception as e:
                logger.warning(f"SSE Bridge: Error streaming events for session {session_id[:8]}...: {e}")
            finally:
                logger.info(f"SSE Bridge: Event loop ended for session {session_id[:8]}...")
            
        except Exception as e:
            logger.error(f"SSE Bridge: Error creating session for channel '{channel}': {e}")
            # Send error response
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [(b"content-type", b"application/json")] + self._get_cors_headers(scope)
            })
            error_response = {
                "success": False,
                "error": f"Ошибка создания сессии: {str(e)} / Session creation error: {str(e)}"
            }
            await send({
                "type": "http.response.body",
                "body": json.dumps(error_response).encode()
            })
            return
        
        finally:
            # Cleanup session
            if 'session_id' in locals():
                try:
                    await bridge_session_manager.cleanup_session(session_id)
                    # Unregister from channel registry
                    channel_registry.unregister(session_id)
                    logger.info(f"SSE Bridge: Session {session_id[:8]}... cleaned up")
                except Exception as e:
                    logger.error(f"SSE Bridge: Error cleaning up session {session_id[:8]}...: {e}")
    
    async def handle_post_message(
        self, 
        scope: Scope, 
        receive: Receive, 
        send: Send
    ) -> None:
        """
        Handle POST message from SuperAssistant.
        
        This method:
        1. Handles OPTIONS preflight requests for CORS
        2. Extracts session_id from query parameters
        3. Validates the session exists
        4. Parses the JSON-RPC message from request body
        5. Forwards the message to the internal Streamable HTTP session
        6. Sends the response back via SSE data event
        
        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
            
        Validates: Requirements 3.2, 3.3, 6.1, 6.2, 6.3, 7.1-7.6, 8.3, 8.4
        """
        # Handle OPTIONS preflight request
        if scope.get("method") == "OPTIONS":
            await self._handle_options_request(scope, send)
            return
        
        try:
            # Extract session_id from query parameters
            session_id = self._extract_session_id(scope)
            session = None
            
            if session_id:
                # Standard case: session_id provided
                session = bridge_session_manager.get_session(session_id)
                if not session:
                    await self._send_error_response(
                        send, 404,
                        "Сессия не найдена / Session not found",
                        scope
                    )
                    return
            else:
                # Fallback case: no session_id, try to find by channel
                # This handles misconfigured clients that POST to /sse?channel=X
                channel = self._extract_and_validate_channel(scope)
                session = bridge_session_manager.get_session_by_channel(channel)
                
                if not session:
                    await self._send_error_response(
                        send, 404,
                        f"Нет активной сессии для канала '{channel}' / No active session for channel '{channel}'",
                        scope
                    )
                    return
                
                session_id = session.session_id
                logger.info(f"SSE Bridge: Using session {session_id[:8]}... for channel '{channel}' (fallback)")
            
            logger.debug(f"SSE Bridge: POST message for session {session_id[:8]}...")
            
            # Read and parse request body
            try:
                body = await self._read_request_body(receive)
                message = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.warning(f"SSE Bridge: JSON parse error in session {session_id[:8]}...: {e}")
                await self._send_error_response(
                    send, 400,
                    f"Ошибка разбора JSON: {str(e)} / JSON parse error: {str(e)}",
                    scope
                )
                return
            except Exception as e:
                logger.error(f"SSE Bridge: Error reading request body for session {session_id[:8]}...: {e}")
                await self._send_error_response(
                    send, 400,
                    f"Ошибка чтения запроса: {str(e)} / Request read error: {str(e)}",
                    scope
                )
                return
            
            # Forward message to Streamable HTTP
            try:
                # Forward message to real MCP server
                response = await self._forward_to_mcp_server(message, session)
                
                logger.debug(
                    f"SSE Bridge: Real MCP response generated for session {session_id[:8]}...: "
                    f"{message.get('method', 'unknown')}"
                )
                
                # Send response via SSE data event
                data_event = SseEventFormatter.format_data_event(response)
                logger.info(f"SSE Bridge: Sending SSE data event for session {session_id[:8]}...")
                logger.debug(f"SSE Bridge: Event content: {data_event}")
                await session.sse_stream.send(data_event)
                
                logger.info(f"SSE Bridge: Response sent via SSE for session {session_id[:8]}...")
                
                # Send success response to POST
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")]
                })
                await send({
                    "type": "http.response.body",
                    "body": json.dumps({"success": True}).encode()
                })
                
            except Exception as e:
                logger.error(f"SSE Bridge: Error processing message for session {session_id[:8]}...: {e}")
                await self._send_error_response(
                    send, 500,
                    f"Внутренняя ошибка сервера: {str(e)} / Internal server error: {str(e)}",
                    scope
                )
                return
        
        except Exception as e:
            logger.error(f"SSE Bridge: Unexpected error in handle_post_message: {e}")
            await self._send_error_response(
                send, 500,
                f"Неожиданная ошибка: {str(e)} / Unexpected error: {str(e)}",
                scope
            )
    
    def _extract_and_validate_channel(self, scope: Scope) -> str:
        """
        Extract channel parameter from query string and validate it.
        
        Uses "default" if channel parameter is missing or invalid.
        
        Args:
            scope: ASGI scope dict
            
        Returns:
            Validated channel ID (guaranteed to be valid)
            
        Validates: Requirements 2.3, 2.4, 2.5, 5.1
        """
        query_string = scope.get("query_string", b"").decode()
        if not query_string:
            logger.debug("SSE Bridge: No query string, using default channel")
            return "default"
        
        try:
            parsed = parse_qs(query_string)
            raw_channel = parsed.get("channel", ["default"])[0]
            
            # Validate channel using ChannelRegistry
            validated_channel = ChannelRegistry.validate_channel_id(raw_channel)
            
            if validated_channel != raw_channel:
                logger.warning(
                    f"SSE Bridge: Invalid channel '{raw_channel}', using 'default'"
                )
            else:
                logger.debug(f"SSE Bridge: Using channel '{validated_channel}'")
            
            return validated_channel
            
        except Exception as e:
            logger.warning(f"SSE Bridge: Error parsing channel parameter: {e}, using default")
            return "default"
    
    def _extract_session_id(self, scope: Scope) -> Optional[str]:
        """
        Extract session_id from query parameters.
        
        Args:
            scope: ASGI scope dict
            
        Returns:
            Session ID if found, None otherwise
        """
        query_string = scope.get("query_string", b"").decode()
        if not query_string:
            return None
        
        try:
            parsed = parse_qs(query_string)
            session_id = parsed.get("session_id", [None])[0]
            return session_id
        except Exception as e:
            logger.warning(f"SSE Bridge: Error parsing session_id: {e}")
            return None
    
    async def _read_request_body(self, receive: Receive) -> bytes:
        """
        Read the complete request body from ASGI receive.
        
        Args:
            receive: ASGI receive callable
            
        Returns:
            Complete request body as bytes
        """
        body_parts = []
        
        while True:
            message = await receive()
            if message["type"] == "http.request":
                body_parts.append(message.get("body", b""))
                if not message.get("more_body", False):
                    break
        
        return b"".join(body_parts)
    
    async def _send_sse_event(self, send: Send, event: Dict[str, str]) -> None:
        """
        Send SSE event in proper format.
        
        Args:
            send: ASGI send callable
            event: Event dict with 'event' and 'data' keys
        """
        event_text = f"event: {event['event']}\ndata: {event['data']}\n\n"
        await send({
            "type": "http.response.body",
            "body": event_text.encode('utf-8'),
            "more_body": True
        })
    
    def _get_cors_headers(self, scope: Scope) -> list:
        """
        Get CORS headers based on request origin and configuration.
        
        Args:
            scope: ASGI scope dict
            
        Returns:
            List of header tuples for CORS
        """
        headers = []
        
        # Extract origin from headers
        origin = None
        for key, value in scope.get("headers", []):
            if key.decode("latin1").lower() == "origin":
                origin = value.decode("latin1")
                break
        
        # Determine allowed origin
        allowed_origin = None
        
        if settings.cors_allow_all:
            allowed_origin = "*"
        elif origin:
            # Always allow browser extensions
            if origin.startswith("chrome-extension://") or origin.startswith("moz-extension://"):
                allowed_origin = origin
            elif origin in settings.cors_origins:
                allowed_origin = origin
        
        # Add CORS headers if origin is allowed
        if allowed_origin:
            headers.extend([
                (b"access-control-allow-origin", allowed_origin.encode()),
                (b"access-control-allow-methods", b"GET, POST, OPTIONS"),
                (b"access-control-allow-headers", b"Accept, Content-Type, Origin"),
                (b"access-control-max-age", b"86400"),
            ])
        
        return headers
    
    async def _handle_options_request(self, scope: Scope, send: Send) -> None:
        """
        Handle OPTIONS preflight request for CORS.
        
        Args:
            scope: ASGI scope dict
            send: ASGI send callable
            
        Validates: Requirements 6.1, 6.2, 6.3, 6.4
        """
        cors_headers = self._get_cors_headers(scope)
        
        if cors_headers:
            # CORS allowed - send 204 No Content
            await send({
                "type": "http.response.start",
                "status": 204,
                "headers": cors_headers
            })
            await send({
                "type": "http.response.body",
                "body": b""
            })
            logger.debug("SSE Bridge: OPTIONS preflight request approved")
        else:
            # CORS not allowed - send 403 Forbidden
            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": [(b"content-type", b"application/json")]
            })
            error_response = {
                "success": False,
                "error": "Источник не разрешен / Origin not allowed"
            }
            await send({
                "type": "http.response.body",
                "body": json.dumps(error_response, ensure_ascii=False).encode('utf-8')
            })
            logger.warning("SSE Bridge: OPTIONS preflight request rejected")
    
    async def _send_error_response(
        self, 
        send: Send, 
        status_code: int, 
        error_message: str,
        scope: Optional[Scope] = None
    ) -> None:
        """
        Send error response with bilingual message and CORS headers.
        
        Args:
            send: ASGI send callable
            status_code: HTTP status code
            error_message: Bilingual error message
            scope: ASGI scope dict for CORS headers (optional)
            
        Validates: Requirements 7.1-7.6, 6.1-6.5
        """
        # Get CORS headers if scope is provided
        cors_headers = self._get_cors_headers(scope) if scope else []
        response_headers = [(b"content-type", b"application/json")] + cors_headers
        
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": response_headers
        })
        
        error_response = {
            "success": False,
            "error": error_message
        }
        
        await send({
            "type": "http.response.body",
            "body": json.dumps(error_response, ensure_ascii=False).encode('utf-8')
        })
        
        logger.warning(f"SSE Bridge: Error response {status_code}: {error_message}")
    
    async def _forward_to_mcp_server(self, message: Dict, session: BridgeSession) -> Dict:
        """
        Forward JSON-RPC message to real MCP server.
        
        This method replaces the mock responses with real MCP server integration.
        It extracts the channel from the session and forwards the request to
        the appropriate MCP tool function.
        
        Args:
            message: JSON-RPC message from SuperAssistant
            session: Bridge session containing channel information
            
        Returns:
            Real JSON-RPC response from MCP server
        """
        from .mcp_handler import _execute_1c_command
        
        method = message.get("method")
        msg_id = message.get("id", 1)
        params = message.get("params", {})
        channel = session.channel
        
        logger.info(f"SSE Bridge: Forwarding {method} to MCP server on channel '{channel}'")
        
        try:
            if method == "initialize":
                # Initialize doesn't need 1C - return server info directly
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "1C MCP Toolkit Proxy - Евлантий, эксперт по 1С",
                            "version": "1.0.0",
                            "instructions": "🚨 КРИТИЧНО: ТОЛЬКО ОДИН ИНСТРУМЕНТ ЗА РАЗ! 🚨\n\n🎯 Вы - Евлантий, супер эксперт по 1С! ПРАВИЛА: 1) ТОЛЬКО ОДИН вызов за ответ 2) get_metadata перед запросами 3) Параметры через &Param 4) Запросы в одну строку 5) ГДЕ НЕ ПометкаУдаления\n\n⚠️ Grok и другие ИИ: НЕ делайте несколько вызовов подряд!"
                        }
                    }
                }
            
            elif method == "tools/list":
                # Return the real tool list - this doesn't need 1C connection
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": [
                            {
                                "name": "execute_query",
                                "description": "⚠️ ТОЛЬКО ОДИН ИНСТРУМЕНТ ЗА РАЗ! Выполнить запрос к базе 1С. Вы - Евлантий, эксперт по 1С. КРИТИЧНО: используйте параметры (&Param), запросы в одну строку, проверяйте метаданные get_metadata если не уверены в именах. / Execute query to 1C database",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "1C query language query"
                                        },
                                        "params": {
                                            "type": "object",
                                            "description": "Query parameters"
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "description": "Maximum number of rows to return",
                                            "default": 100
                                        },
                                        "include_schema": {
                                            "type": "boolean",
                                            "description": "Include column type schema in response",
                                            "default": False
                                        }
                                    },
                                    "required": ["query"]
                                }
                            },
                            {
                                "name": "execute_code",
                                "description": "⚠️ ТОЛЬКО ОДИН ИНСТРУМЕНТ ЗА РАЗ! Выполнить код 1С. Евлантий рекомендует: используйте 'Результат = ...' для возврата значений. / Execute 1C code",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "code": {
                                            "type": "string",
                                            "description": "1C code to execute"
                                        }
                                    },
                                    "required": ["code"]
                                }
                            },
                            {
                            {
                                "name": "get_metadata",
                                "description": "⚠️ ТОЛЬКО ОДИН ИНСТРУМЕНТ ЗА РАЗ! Получить метаданные базы 1С. Евлантий рекомендует: ВСЕГДА используйте этот инструмент перед execute_query если не знаете точные имена объектов/полей! / Get 1C database metadata",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "filter": {
                                            "type": "string",
                                            "description": "Полное имя объекта (например, Справочник.Номенклатура) или путь к элементу коллекции"
                                        },
                                        "meta_type": {
                                            "type": ["string", "array"],
                                            "description": "Фильтр типа объекта для списка (строка или массив). Используйте '*' для списка по всем типам"
                                        },
                                        "name_mask": {
                                            "type": "string",
                                            "description": "Маска поиска по имени/синониму (поиск подстроки без учета регистра)"
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "description": "Максимальное количество объектов в списке (по умолчанию: 100, максимум: 1000)",
                                            "default": 100
                                        },
                                        "sections": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Разделы детализации для включения (работает только с filter). Поддерживаются: properties, forms, commands, layouts, predefined, movements, characteristics"
                                        },
                                        "offset": {
                                            "type": "integer",
                                            "description": "Смещение для пагинации в режиме списка (по умолчанию: 0)",
                                            "default": 0
                                        },
                                        "extension_name": {
                                            "type": "string",
                                            "description": "Имя расширения (None=основная конфигурация, ''=список расширений, 'Name'=объекты расширения)"
                                        }
                                    }
                                }
                            },
                            {
                                "name": "get_event_log",
                                "description": "⚠️ ТОЛЬКО ОДИН ИНСТРУМЕНТ ЗА РАЗ! Получить журнал регистрации. Евлантий поможет найти события и ошибки в системе. / Get event log",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "start_date": {
                                            "type": "string",
                                            "description": "Дата начала в формате ISO 8601 (YYYY-MM-DDTHH:MM:SS)"
                                        },
                                        "end_date": {
                                            "type": "string", 
                                            "description": "Дата окончания в формате ISO 8601 (YYYY-MM-DDTHH:MM:SS)"
                                        },
                                        "levels": {
                                            "type": "array",
                                            "items": {"type": "string", "enum": ["Information", "Warning", "Error", "Note"]},
                                            "description": "Список уровней важности для фильтрации"
                                        },
                                        "events": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Список типов событий для фильтрации"
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "description": "Максимальное количество записей (по умолчанию: 100, максимум: 1000)",
                                            "default": 100
                                        },
                                        "object_description": {
                                            "type": "object",
                                            "description": "Описание объекта из результатов execute_query"
                                        },
                                        "link": {
                                            "type": "string",
                                            "description": "Навигационная ссылка в формате e1cib/data/Type.Name?ref=HexGUID"
                                        },
                                        "data": {
                                            "type": "string",
                                            "description": "Ссылка на объект данных (для обратной совместимости)"
                                        },
                                        "metadata_type": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Список типов объектов метаданных для фильтрации"
                                        },
                                        "user": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Список пользователей для фильтрации"
                                        },
                                        "session": {
                                            "type": "array",
                                            "items": {"type": "integer"},
                                            "description": "Список номеров сеансов для фильтрации"
                                        },
                                        "application": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Список приложений для фильтрации"
                                        },
                                        "computer": {
                                            "type": "string",
                                            "description": "Имя компьютера для фильтрации"
                                        },
                                        "comment_contains": {
                                            "type": "string",
                                            "description": "Подстрока для поиска в комментариях"
                                        },
                                        "transaction_status": {
                                            "type": "string",
                                            "enum": ["Committed", "RolledBack", "Unfinished", "Unknown"],
                                            "description": "Статус транзакции для фильтрации"
                                        },
                                        "same_second_offset": {
                                            "type": "integer",
                                            "description": "Смещение для курсорной пагинации (по умолчанию: 0)",
                                            "default": 0
                                        }
                                    }
                                }
                            },
                            {
                                "name": "get_object_by_link",
                                "description": "⚠️ ТОЛЬКО ОДИН ИНСТРУМЕНТ ЗА РАЗ! Получить объект по ссылке. Евлантий поможет получить данные объекта по его ссылке. / Get object by link",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "link": {
                                            "type": "string",
                                            "description": "Навигационная ссылка в формате e1cib/data/ТипОбъекта.ИмяОбъекта?ref=HexGUID (например: e1cib/data/Справочник.Контрагенты?ref=80c6cc1a7e58902811ebcda8cb07c0f5)"
                                        }
                                    },
                                    "required": ["link"]
                                }
                            },
                            {
                                "name": "get_link_of_object",
                                "description": "⚠️ ТОЛЬКО ОДИН ИНСТРУМЕНТ ЗА РАЗ! Получить ссылку объекта. Евлантий поможет создать ссылку на объект для дальнейшего использования. / Get link of object",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "object_description": {
                                            "type": "object",
                                            "description": "Описание объекта с полями {_objectRef: true, УникальныйИдентификатор, ТипОбъекта, Представление}",
                                            "properties": {
                                                "_objectRef": {
                                                    "type": "boolean",
                                                    "description": "Признак описания объекта (должен быть true)"
                                                },
                                                "УникальныйИдентификатор": {
                                                    "type": "string",
                                                    "description": "UUID объекта"
                                                },
                                                "ТипОбъекта": {
                                                    "type": "string",
                                                    "description": "Тип объекта"
                                                },
                                                "Представление": {
                                                    "type": "string",
                                                    "description": "Строковое представление объекта"
                                                }
                                            },
                                            "required": ["_objectRef", "УникальныйИдентификатор", "ТипОбъекта"]
                                        }
                                    },
                                    "required": ["object_description"]
                                }
                            },
                            {
                                "name": "find_references_to_object",
                                "description": "⚠️ ТОЛЬКО ОДИН ИНСТРУМЕНТ ЗА РАЗ! Найти ссылки на объект в базе данных 1С. ВАЖНО: НЕ используйте параметр 'object_link' - он не существует! Используйте только 'target_object_description' и 'search_scope'. Евлантий поможет найти все места использования объекта. / Find references to object in 1C database. IMPORTANT: Do NOT use 'object_link' parameter - it doesn't exist! Use only 'target_object_description' and 'search_scope'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "target_object_description": {
                                            "type": "object",
                                            "description": "Описание целевого объекта из результатов execute_query (НЕ ссылка!) / Target object description from execute_query results (NOT a link!)",
                                            "properties": {
                                                "_objectRef": {
                                                    "type": "boolean",
                                                    "description": "Признак описания объекта (должен быть true)"
                                                },
                                                "УникальныйИдентификатор": {
                                                    "type": "string",
                                                    "description": "UUID объекта"
                                                },
                                                "ТипОбъекта": {
                                                    "type": "string",
                                                    "description": "Тип объекта"
                                                },
                                                "Представление": {
                                                    "type": "string",
                                                    "description": "Строковое представление объекта"
                                                }
                                            },
                                            "required": ["_objectRef", "УникальныйИдентификатор", "ТипОбъекта"]
                                        },
                                        "search_scope": {
                                            "type": "array",
                                            "items": {
                                                "type": "string",
                                                "enum": ["documents", "catalogs", "information_registers", "accumulation_registers", "accounting_registers", "calculation_registers"]
                                            },
                                            "description": "Области поиска. Используйте 'catalogs' для справочников, 'documents' для документов, и т.д. НЕ используйте имена конкретных объектов! / Search areas. Use 'catalogs' for catalogs, 'documents' for documents, etc. Do NOT use specific object names!"
                                        },
                                        "meta_filter": {
                                            "type": "object",
                                            "description": "Фильтр объектов метаданных (опционально)",
                                            "properties": {
                                                "names": {
                                                    "type": "array",
                                                    "items": {"type": "string"},
                                                    "description": "Список точных имён объектов метаданных"
                                                },
                                                "name_mask": {
                                                    "type": "string",
                                                    "description": "Маска для поиска по имени"
                                                }
                                            }
                                        },
                                        "limit_hits": {
                                            "type": "integer",
                                            "description": "Максимальное количество находок",
                                            "default": 200
                                        },
                                        "limit_per_meta": {
                                            "type": "integer",
                                            "description": "Максимальное количество находок на один объект метаданных",
                                            "default": 20
                                        },
                                        "timeout_budget_sec": {
                                            "type": "integer",
                                            "description": "Бюджет времени в секундах",
                                            "default": 30
                                        }
                                    },
                                    "required": ["target_object_description", "search_scope"]
                                }
                            },
                            {
                                "name": "get_access_rights",
                                "description": "⚠️ ТОЛЬКО ОДИН ИНСТРУМЕНТ ЗА РАЗ! Получить права доступа. Евлантий поможет проверить права пользователей на объекты метаданных. / Get access rights",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "metadata_object": {
                                            "type": "string",
                                            "description": "Полное имя объекта метаданных (например, Справочник.Контрагенты, Документ.РеализацияТоваровУслуг)"
                                        },
                                        "user_name": {
                                            "type": "string",
                                            "description": "Имя пользователя для расчета эффективных прав (опционально)"
                                        },
                                        "rights_filter": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Список прав для отображения в результате (опционально)"
                                        },
                                        "roles_filter": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Список ролей для отображения (опционально)"
                                        }
                                    },
                                    "required": ["metadata_object"]
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                # Forward tool calls to real MCP server
                tool_name = params.get("name")
                tool_arguments = params.get("arguments", {})
                
                if not tool_name:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32602,
                            "message": "Invalid params: missing tool name"
                        }
                    }
                
                logger.info(f"SSE Bridge: Executing tool '{tool_name}' with args: {tool_arguments}")
                
                # Execute the tool via MCP server
                result = await _execute_1c_command(tool_name, tool_arguments, channel)
                
                # Convert MCP result to JSON-RPC format
                if result.get("success"):
                    # Success case - return the data
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result.get("data"), ensure_ascii=False, indent=2)
                                }
                            ]
                        }
                    }
                else:
                    # Error case - return the error
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32603,
                            "message": result.get("error", "Unknown error")
                        }
                    }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            logger.error(f"SSE Bridge: Error forwarding to MCP server: {e}")
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }


# Global instance for use by the server
superassistant_bridge = SuperAssistantSseBridge(None)  # Will be initialized with mcp_server in server.py