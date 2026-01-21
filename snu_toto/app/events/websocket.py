from typing import Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, event_id: str):
        await websocket.accept()
        if event_id not in self.active_connections:
            self.active_connections[event_id]=set()
        self.active_connections[event_id].add(websocket)

    def disconnect(self, websocket: WebSocket, event_id: str):
        if event_id in self.active_connections:
            self.active_connections[event_id].discard(websocket)
            if not self.active_connections[event_id]:
                #빈 Set을 딕셔너리에서 제거하여 메모리 정리
                del self.active_connections[event_id]

    async def broadcast_to_event(self, event_id: str, message: dict):
        """특정 이벤트 구독작들에게 메세지 전송"""
        if event_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[event_id]:
                try:
                    await connection.send_json(message)

                except Exception:
                    disconnected.add(connection)

            for conn in disconnected:
                self.disconnect(conn, event_id)

manager = ConnectionManager()
