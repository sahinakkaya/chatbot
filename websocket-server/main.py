from fastapi import WebSocket, Query
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = set()
        self.active_connections[room].add(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        self.active_connections[room].remove(websocket)
        if not self.active_connections[room]:
            del self.active_connections[room]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, room: str):
        if room in self.active_connections:
            for connection in self.active_connections[room]:
                await connection.send_text(message)


conn_manager = ConnectionManager()


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, 
    token: str = Query(...),
    userid: str = Query(...)):
    room = f"room_{token}"
    await conn_manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_text()
            await conn_manager.send_personal_message(f"You wrote: {data}", websocket)
            await conn_manager.broadcast(f"User {userid} says: {data}", room)
    except WebSocketDisconnect:
        conn_manager.disconnect(websocket, room)
        await conn_manager.broadcast(f"User {userid} left the chat", room)
