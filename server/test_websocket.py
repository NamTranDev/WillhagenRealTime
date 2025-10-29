#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test WebSocket để kiểm tra hệ thống realtime
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    """Test WebSocket connection"""
    uri = "ws://localhost:8000/ws"
    
    try:
        print("🔌 Connecting to WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket!")
            
            # Đợi và nhận messages
            print("📡 Listening for messages...")
            message_count = 0
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(message)
                    message_count += 1
                    
                    print(f"\n📨 Message #{message_count}:")
                    print(f"   Type: {data.get('type', 'N/A')}")
                    print(f"   Timestamp: {data.get('timestamp', 'N/A')}")
                    
                    if data.get('type') == 'new_listing':
                        listing = data.get('data', {})
                        print(f"   🚗 New Car Found:")
                        print(f"      ID: {listing.get('id', 'N/A')}")
                        print(f"      Title: {listing.get('title', 'N/A')}")
                        print(f"      Price: {listing.get('price', 'N/A')}")
                        print(f"      Year: {listing.get('year', 'N/A')}")
                        print(f"      Mileage: {listing.get('mileage', 'N/A')}")
                        print(f"      Fuel: {listing.get('fuel', 'N/A')}")
                        print(f"      Brand: {listing.get('brand', 'N/A')}")
                        print(f"      Model: {listing.get('model', 'N/A')}")
                        print(f"      Location: {listing.get('location', 'N/A')}")
                        print(f"      URL: {listing.get('url', 'N/A')}")
                        print(f"      Crawled at: {listing.get('crawled_at', 'N/A')}")
                    
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for message, reconnecting...")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("❌ WebSocket connection closed")
                    break
                except Exception as e:
                    print(f"❌ Error receiving message: {e}")
                    break
                    
    except ConnectionRefusedError:
        print("❌ Cannot connect to WebSocket server. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error connecting to WebSocket: {e}")

async def main():
    print("🚀 Testing Willhaben Realtime WebSocket")
    print("=" * 50)
    
    await test_websocket()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
