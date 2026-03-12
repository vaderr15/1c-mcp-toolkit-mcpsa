"""
Bridge Session Manager for SuperAssistant SSE Bridge.

This module manages sessions for the SuperAssistant SSE bridge, mapping
SSE connections to Streamable HTTP sessions with proper lifecycle management.

Validates: Requirements 2.6, 2.7, 3.5, 3.6
"""

import asyncio
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from anyio.streams.memory import MemoryObjectSendStream

logger = logging.getLogger(__name__)


@dataclass
class BridgeSession:
    """
    Active bridge session between SuperAssistant SSE and Streamable HTTP.
    
    Represents the state of a single SuperAssistant connection, including
    the mapping to internal Streamable HTTP session and SSE event stream.
    """
    
    session_id: str
    """Unique session identifier (cryptographically secure hex string)."""
    
    channel: str
    """Channel ID for isolation (validated via ChannelRegistry)."""
    
    streamable_session_id: str
    """Internal Streamable HTTP session ID for MCP communication."""
    
    sse_stream: MemoryObjectSendStream[dict]
    """Stream for sending SSE events to SuperAssistant client."""
    
    created_at: datetime
    """Session creation timestamp for monitoring and cleanup."""
    
    last_activity: datetime
    """Last activity timestamp for timeout detection."""


class BridgeSessionManager:
    """
    Manages sessions for the SuperAssistant SSE bridge.
    
    Responsibilities:
    - Generate unique session IDs using cryptographically secure random
    - Store session_id → BridgeSession mapping
    - Provide session lookup and channel retrieval
    - Handle session cleanup and resource management
    - Track active sessions for monitoring
    
    Thread-safe for concurrent access from multiple SSE connections.
    """
    
    def __init__(self):
        """Initialize the session manager with empty session storage."""
        self._sessions: Dict[str, BridgeSession] = {}
        self._lock = asyncio.Lock()  # Protect concurrent access to _sessions
        logger.info("Bridge session manager initialized")
    
    def create_session(
        self, 
        channel: str,
        streamable_session_id: str,
        sse_stream: MemoryObjectSendStream[dict]
    ) -> str:
        """
        Create a new bridge session with unique session_id.
        
        Generates a cryptographically secure session ID and stores the session
        mapping. The session ID is used by SuperAssistant to identify the
        connection when sending POST messages.
        
        Args:
            channel: Channel ID for isolation (should be pre-validated)
            streamable_session_id: Internal Streamable HTTP session ID
            sse_stream: Stream for sending SSE events to client
            
        Returns:
            Unique session_id (hex string) for the new session
            
        Validates: Requirements 2.6, 2.7
        - 2.6: Generate unique session_id for each connection
        - 2.7: Register session_id to specified channel
        """
        # Generate cryptographically secure session ID (32 bytes = 64 hex chars)
        # This ensures uniqueness across all concurrent sessions
        session_id = secrets.token_hex(32)
        
        now = datetime.now()
        session = BridgeSession(
            session_id=session_id,
            channel=channel,
            streamable_session_id=streamable_session_id,
            sse_stream=sse_stream,
            created_at=now,
            last_activity=now
        )
        
        # Store session (no async lock needed for dict assignment)
        self._sessions[session_id] = session
        
        logger.info(
            f"Bridge session created: {session_id[:8]}... "
            f"for channel '{channel}' with streamable session {streamable_session_id[:8]}..."
        )
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[BridgeSession]:
        """
        Get session by ID.
        
        Args:
            session_id: The session ID to look up
            
        Returns:
            BridgeSession if found, None otherwise
            
        Validates: Requirements 3.5
        - 3.5: Maintain session state between SSE connection and Streamable HTTP
        """
        session = self._sessions.get(session_id)
        
        if session:
            # Update last activity timestamp
            session.last_activity = datetime.now()
            logger.debug(f"Session {session_id[:8]}... accessed, updated activity timestamp")
        else:
            logger.debug(f"Session {session_id[:8]}... not found")
        
        return session
    
    def get_channel(self, session_id: str) -> str:
        """
        Get channel for session.
        
        Args:
            session_id: The session ID to look up
            
        Returns:
            Channel ID for the session, or "default" if session not found
            
        Validates: Requirements 3.5
        - 3.5: Maintain session state for channel routing
        """
        session = self._sessions.get(session_id)
        if session:
            return session.channel
        
        logger.warning(f"Session {session_id[:8]}... not found, returning default channel")
        return "default"
    
    async def cleanup_session(self, session_id: str) -> None:
        """
        Clean up session and associated resources.
        
        Removes the session from storage and closes the SSE stream.
        This should be called when the SSE connection is closed or
        when the session times out.
        
        Args:
            session_id: The session ID to clean up
            
        Validates: Requirements 3.6
        - 3.6: Clean up corresponding Streamable HTTP session when SSE disconnects
        """
        async with self._lock:
            session = self._sessions.pop(session_id, None)
        
        if session:
            try:
                # Close the SSE stream to release resources
                await session.sse_stream.aclose()
                logger.info(
                    f"Bridge session cleaned up: {session_id[:8]}... "
                    f"from channel '{session.channel}'"
                )
            except Exception as e:
                logger.warning(
                    f"Error closing SSE stream for session {session_id[:8]}...: {e}"
                )
        else:
            logger.debug(f"Session {session_id[:8]}... not found during cleanup")
    
    def get_session_by_channel(self, channel: str) -> Optional[BridgeSession]:
        """
        Get the most recent active session for a channel.
        
        This is a fallback method for clients that don't properly use session_id.
        
        Args:
            channel: The channel ID to look up
            
        Returns:
            Most recent BridgeSession for the channel, or None if not found
        """
        matching_sessions = []
        
        for session in self._sessions.values():
            if session.channel == channel:
                matching_sessions.append(session)
        
        if not matching_sessions:
            logger.debug(f"No sessions found for channel '{channel}'")
            return None
        
        # Return the most recently created session
        most_recent = max(matching_sessions, key=lambda s: s.created_at)
        logger.debug(f"Found session {most_recent.session_id[:8]}... for channel '{channel}'")
        return most_recent
    
    def get_stats(self) -> dict:
        """
        Get statistics about active sessions for monitoring.
        
        Returns:
            Dictionary with session statistics including:
            - active_sessions: Total number of active sessions
            - sessions_by_channel: Sessions grouped by channel
            - oldest_session_age: Age of oldest session in seconds
            - newest_session_age: Age of newest session in seconds
            
        Validates: Requirements monitoring and debugging support
        """
        now = datetime.now()
        sessions_by_channel: Dict[str, int] = {}
        session_ages = []
        
        for session in self._sessions.values():
            # Count sessions by channel
            channel = session.channel
            sessions_by_channel[channel] = sessions_by_channel.get(channel, 0) + 1
            
            # Calculate session age
            age_seconds = (now - session.created_at).total_seconds()
            session_ages.append(age_seconds)
        
        stats = {
            "active_sessions": len(self._sessions),
            "sessions_by_channel": sessions_by_channel,
        }
        
        if session_ages:
            stats["oldest_session_age"] = max(session_ages)
            stats["newest_session_age"] = min(session_ages)
        else:
            stats["oldest_session_age"] = 0
            stats["newest_session_age"] = 0
        
        return stats
    
    async def cleanup_expired_sessions(self, max_age_seconds: float = 3600) -> int:
        """
        Clean up sessions that have been inactive for too long.
        
        This is a maintenance method that should be called periodically
        to prevent memory leaks from abandoned sessions.
        
        Args:
            max_age_seconds: Maximum age for sessions (default: 1 hour)
            
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now()
        expired_sessions = []
        
        # Find expired sessions
        for session_id, session in self._sessions.items():
            age_seconds = (now - session.last_activity).total_seconds()
            if age_seconds > max_age_seconds:
                expired_sessions.append(session_id)
        
        # Clean up expired sessions
        cleanup_count = 0
        for session_id in expired_sessions:
            await self.cleanup_session(session_id)
            cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} expired bridge sessions")
        
        return cleanup_count


# Global instance for use by the bridge
bridge_session_manager = BridgeSessionManager()