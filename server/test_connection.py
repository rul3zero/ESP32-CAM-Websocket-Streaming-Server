import asyncio
import websockets
import json
import time

async def test_websocket():
    # Test different possible server IPs
    test_ips = [
        "192.168.56.1",  # Current detected IP
        "192.168.8.100", # Your ethernet IP
        "192.168.1.100", # Common router IP range
        "localhost",     # Local testing
        "127.0.0.1"      # Local testing
    ]
    
    port = 3000
    
    for ip in test_ips:
        try:
            uri = f"ws://{ip}:{port}/ws"
            print(f"Testing connection to: {uri}")
            
            async with websockets.connect(uri, timeout=5) as websocket:
                print(f"✅ Successfully connected to {uri}")
                
                # Send test device ID
                await websocket.send("TEST_CLIENT")
                print("📤 Sent device ID: TEST_CLIENT")
                
                # Wait for a response or timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    print(f"📥 Received: {response}")
                except asyncio.TimeoutError:
                    print("⏰ No response received (timeout)")
                
                return ip  # Return successful IP
                
        except Exception as e:
            print(f"❌ Failed to connect to {uri}: {e}")
    
    print("🚫 Could not connect to any server")
    return None

if __name__ == "__main__":
    print("🔍 Testing WebSocket Server Connectivity...")
    print("=" * 50)
    
    successful_ip = asyncio.run(test_websocket())
    
    if successful_ip:
        print(f"\n🎉 Server is reachable at: {successful_ip}:3000")
        print(f"📋 Update your ESP32-CAM code to use: ws://{successful_ip}:3000/ws")
    else:
        print("\n⚠️  No server found. Make sure the Python server is running.")
