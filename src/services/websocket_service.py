"""
WebSocket Service for DBSyncr
Handles real-time updates for long-running operations.
"""
import json
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from utils.logging_config import get_logger


class WebSocketService:
    """Service for managing WebSocket connections and real-time updates."""

    def __init__(self):
        self.logger = get_logger("WebSocketService")
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_clients: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a WebSocket client."""
        await websocket.accept()
        self.logger.info(f"WebSocket client connected: {client_id}")

        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
        self.connection_clients[websocket] = client_id

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        client_id = self.connection_clients.get(websocket)
        if client_id and client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

        if websocket in self.connection_clients:
            del self.connection_clients[websocket]

        self.logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            self.logger.error(f"Failed to send message to client: {e}")
            self.disconnect(websocket)

    async def broadcast_to_client(self, message: Dict[str, Any], client_id: str):
        """Broadcast a message to all connections for a specific client."""
        if client_id not in self.active_connections:
            return

        disconnected = []
        for websocket in self.active_connections[client_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                self.logger.error(f"Failed to send broadcast to client {client_id}: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)

    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for client_connections in self.active_connections.values():
            for websocket in client_connections:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    self.logger.error(f"Failed to send global broadcast: {e}")
                    disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)

    async def send_progress_update(self, client_id: str, operation: str, progress: float, message: str = None):
        """Send a progress update for a long-running operation."""
        await self.broadcast_to_client({
            "type": "progress",
            "operation": operation,
            "progress": progress,
            "message": message,
            "timestamp": self._get_timestamp()
        }, client_id)

    async def send_operation_status(self, client_id: str, operation: str, status: str, details: Dict[str, Any] = None):
        """Send operation status update."""
        await self.broadcast_to_client({
            "type": "status",
            "operation": operation,
            "status": status,
            "details": details or {},
            "timestamp": self._get_timestamp()
        }, client_id)

    async def send_error(self, client_id: str, operation: str, error: str, details: Dict[str, Any] = None):
        """Send error notification."""
        await self.broadcast_to_client({
            "type": "error",
            "operation": operation,
            "error": error,
            "details": details or {},
            "timestamp": self._get_timestamp()
        }, client_id)

    async def send_success(self, client_id: str, operation: str, result: Dict[str, Any] = None):
        """Send success notification."""
        await self.broadcast_to_client({
            "type": "success",
            "operation": operation,
            "result": result or {},
            "timestamp": self._get_timestamp()
        }, client_id)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def get_client_connections(self, client_id: str) -> int:
        """Get number of active connections for a client."""
        return len(self.active_connections.get(client_id, set()))

    def get_total_connections(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.active_connections.values())