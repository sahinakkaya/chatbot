"""
Simple script to test a single WebSocket connection
Measures connection time and message roundtrip
"""
import asyncio
import json
import time

import websockets

WEBSOCKET_URL = "ws://localhost:8080/ws"
USER_ID = "testuser"
TOKEN = "sr6IqwuvN_ciTM_LG2i7OE8PtOJNkMkgdLuTyS4aACk"


async def test_single_connection():
    """Test a single WebSocket connection"""
    url = f"{WEBSOCKET_URL}?token={TOKEN}&userid={USER_ID}"

    print(f"Connecting to {url}")

    # Measure connection time
    connect_start = time.time()

    try:
        async with websockets.connect(url) as websocket:
            connect_time = time.time() - connect_start
            print(f"✓ Connected in {connect_time:.3f} seconds")

            # Send a test message
            message = {
                "type": "message",
                "content": "Hello, this is a test message",
                "userid": USER_ID
            }

            send_start = time.time()
            await websocket.send(json.dumps(message))
            print(f"✓ Message sent in {time.time() - send_start:.3f} seconds")

            # Wait for response
            print("Waiting for response...")
            response_start = time.time()

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_time = time.time() - response_start

                data = json.loads(response)
                print(f"✓ Response received in {response_time:.3f} seconds")
                print(f"Response type: {data.get('type')}")
                print(f"Response content: {data.get('content')}")

                if 'processing_time_ms' in data:
                    print(f"Processing time: {data['processing_time_ms']}ms")

            except asyncio.TimeoutError:
                print("✗ No response received within 10 seconds")

            # Keep connection open for a moment
            await asyncio.sleep(1)

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("SINGLE CONNECTION TEST")
    print("=" * 60)

    start_time = time.time()
    asyncio.run(test_single_connection())
    total_time = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"Total test time: {total_time:.3f} seconds")
    print("=" * 60)
