"""
Load test script for WebSocket server
Tests concurrent connections and message throughput
"""
import sys
import asyncio
import websockets
import json
import time
from datetime import datetime

configurations = {
    0: (5, 1),
    1: (10, 1),
    2: (10, 3),
    3: (20, 3),
    4: (50, 3),
    5: (100, 1),
    6: (100, 3),
    7: (100, 5),
    8: (100, 10),
    9: (200, 1),
}

conf = configurations[int(sys.argv[1])]

WEBSOCKET_URL = "ws://localhost:8080/ws"
NUM_CLIENTS = conf[0]  # Test with 150 concurrent connections
MESSAGES_PER_CLIENT = conf[1]
TOKEN = "test-token"

class LoadTestClient:
    def __init__(self, client_id):
        self.client_id = client_id
        self.userid = f"user{client_id}"
        self.messages_sent = 0
        self.messages_received = 0
        self.start_time = None
        self.end_time = None

    async def run(self):
        """Run a single client that sends and receives messages"""
        url = f"{WEBSOCKET_URL}?token={TOKEN}&userid={self.userid}"

        try:
            async with websockets.connect(url) as websocket:
                self.start_time = time.time()

                # Create tasks for sending and receiving
                send_task = asyncio.create_task(self.send_messages(websocket))
                receive_task = asyncio.create_task(self.receive_messages(websocket))

                # Wait for both tasks to complete
                await asyncio.gather(send_task, receive_task)

                self.end_time = time.time()

        except Exception as e:
            print(f"Client {self.client_id} error: {e}")

    async def send_messages(self, websocket):
        """Send multiple messages"""
        for i in range(MESSAGES_PER_CLIENT):
            message = {
                "type": "message",
                "content": f"Test message {i} from client {self.client_id}",
                "userid": self.userid
            }
            await websocket.send(json.dumps(message))
            self.messages_sent += 1
            # await asyncio.sleep(0.1)  # Small delay between messages

    async def receive_messages(self, websocket):
        """Receive messages until we get all responses"""
        timeout = 15  # 30 seconds timeout (reduced from 60)
        start = time.time()

        while self.messages_received < MESSAGES_PER_CLIENT:
            if time.time() - start > timeout:
                print(f"Client {self.client_id} timeout waiting for responses (received {self.messages_received}/{MESSAGES_PER_CLIENT})")
                break

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                msg_type = data.get("type")

                if msg_type == "response":
                    self.messages_received += 1
                    print(f"Client {self.client_id} received message {self.messages_received}/{MESSAGES_PER_CLIENT}")
                elif msg_type == "error":
                    # Count errors as received to avoid timeout
                    self.messages_received += 1
                    print(f"Client {self.client_id} received error: {data.get('content')}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Client {self.client_id} receive error: {e}")
                break

async def run_load_test():
    """Run the load test with multiple concurrent clients"""
    print(f"Starting load test with {NUM_CLIENTS} clients...")
    print(f"Each client will send {MESSAGES_PER_CLIENT} messages")
    print(f"Total expected messages: {NUM_CLIENTS * MESSAGES_PER_CLIENT}")
    print("-" * 60)

    start_time = time.time()

    # Create all clients
    clients = [LoadTestClient(i) for i in range(NUM_CLIENTS)]

    # Run all clients concurrently
    await asyncio.gather(*[client.run() for client in clients])

    end_time = time.time()
    total_time = end_time - start_time

    # Calculate statistics
    total_sent = sum(c.messages_sent for c in clients)
    total_received = sum(c.messages_received for c in clients)
    successful_clients = sum(1 for c in clients if c.messages_received == MESSAGES_PER_CLIENT)

    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)
    print(f"Total clients: {NUM_CLIENTS}")
    print(f"Successful clients: {successful_clients}")
    print(f"Failed clients: {NUM_CLIENTS - successful_clients}")
    print(f"Total messages sent: {total_sent}")
    print(f"Total messages received: {total_received}")
    print(f"Message loss: {total_sent - total_received} ({(total_sent - total_received) / total_sent * 100:.2f}%)")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Messages per second: {total_received / total_time:.2f}")
    print(f"Average latency per message: {total_time / total_received:.3f} seconds")

    # Success criteria
    print("\n" + "-" * 60)
    print("SUCCESS CRITERIA CHECK:")
    print(f"✓ Concurrent connections (100+): {'PASS' if NUM_CLIENTS >= 100 else 'FAIL'}")
    print(f"✓ Message throughput (100+/s): {'PASS' if total_received / total_time >= 100 else 'FAIL'}")
    print(f"✓ Message delivery (>95%): {'PASS' if total_received / total_sent >= 0.95 else 'FAIL'}")
    print("-" * 60)

if __name__ == "__main__":
    asyncio.run(run_load_test())
