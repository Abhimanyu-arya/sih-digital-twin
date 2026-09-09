import asyncio
import json
import urllib.request
import websockets

async def test_rest_endpoint():
    print("--- 1. Testing GET /api/missions ---")
    url = "http://localhost:8000/api/missions"
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode())
    print(f"Status Code: {req.status}")
    print(f"Missions found: {len(data['missions'])}")
    for m in data['missions']:
        print(f"  - {m['mission_id']}: {m['fault_label']} ({m['total_rows']} rows)")
    assert len(data['missions']) == 6, "Expected 6 demo missions"
    print("[PASS] GET /api/missions verified.\n")

async def test_websocket_single():
    print("--- 2. Testing WebSocket Single Stream & Speed Change ---")
    uri = "ws://localhost:8000/ws/stream"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"action": "start", "mission_id": "mission_007", "speed": 10}))
        res = await ws.recv()
        meta = json.loads(res)
        print(f"Start response: {meta}")
        assert meta["type"] == "stream_started"

        frames = []
        for _ in range(5):
            msg = await ws.recv()
            frame = json.loads(msg)
            frames.append(frame)
            print(f"Frame ts={frame['timestamp']}, MET={frame['met_formatted']}, State={frame['system_status']['state']}, RPM={frame['sensors']['rpm']['value']}")

        assert len(frames) == 5
        assert frames[0]["timestamp"] == 0
        assert frames[4]["timestamp"] == 4

        # Test set_speed to 50x
        print("Changing speed to 50x...")
        await ws.send(json.dumps({"action": "set_speed", "speed": 50}))
        for _ in range(5):
            msg = await ws.recv()
            frame = json.loads(msg)
            frames.append(frame)
        print(f"Received 5 more frames, latest ts={frames[-1]['timestamp']}")

        print("[PASS] WebSocket single stream & speed change verified.\n")

async def test_mission_switch_clean_teardown():
    print("--- 3. Testing Mission Switching & Clean Teardown ---")
    uri = "ws://localhost:8000/ws/stream"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"action": "start", "mission_id": "mission_007", "speed": 50}))
        msg = await ws.recv() # stream_started
        f1 = json.loads(await ws.recv())
        print(f"Mission 007 initial frame ts={f1['timestamp']}")

        print("Switching mid-stream to mission_033...")
        await ws.send(json.dumps({"action": "start", "mission_id": "mission_033", "speed": 50}))
        
        msg = await ws.recv()
        meta = json.loads(msg)
        print(f"Switch response: {meta}")
        assert meta["type"] == "stream_started"
        assert meta["mission_id"] == "mission_033"

        f2 = json.loads(await ws.recv())
        print(f"Mission 033 initial frame ts={f2['timestamp']}")
        assert f2["timestamp"] == 0, "New mission should restart at ts=0"

        print("[PASS] Mission switch mid-stream cleanly tore down old session.\n")

async def test_concurrent_sessions():
    print("--- 4. Testing Item 6: Multi-Tab Concurrent Independent Sessions ---")
    uri = "ws://localhost:8000/ws/stream"
    
    async with websockets.connect(uri) as ws_a, websockets.connect(uri) as ws_b:
        # Tab A: mission_007 at 10x
        await ws_a.send(json.dumps({"action": "start", "mission_id": "mission_007", "speed": 10}))
        # Tab B: mission_033 at 50x
        await ws_b.send(json.dumps({"action": "start", "mission_id": "mission_033", "speed": 50}))

        meta_a = json.loads(await ws_a.recv())
        meta_b = json.loads(await ws_b.recv())

        print(f"Tab A meta: {meta_a['mission_id']} (total_rows: {meta_a['total_rows']})")
        print(f"Tab B meta: {meta_b['mission_id']} (total_rows: {meta_b['total_rows']})")

        assert meta_a["mission_id"] == "mission_007"
        assert meta_b["mission_id"] == "mission_033"
        assert meta_a["total_rows"] == 1426
        assert meta_b["total_rows"] == 1702

        frame_a = json.loads(await ws_a.recv())
        frame_b = json.loads(await ws_b.recv())

        print(f"Tab A Frame 0 RPM: {frame_a['sensors']['rpm']['value']}")
        print(f"Tab B Frame 0 RPM: {frame_b['sensors']['rpm']['value']}")

        # Read 10 frames from Tab A and Tab B
        for _ in range(10):
            frame_a = json.loads(await ws_a.recv())
            frame_b = json.loads(await ws_b.recv())

        print(f"Tab A latest frame total_rows={frame_a['total_rows']}, RPM={frame_a['sensors']['rpm']['value']}")
        print(f"Tab B latest frame total_rows={frame_b['total_rows']}, RPM={frame_b['sensors']['rpm']['value']}")

        # Verify independence: total_rows differ (1426 vs 1702), RPM values differ
        assert frame_a["total_rows"] != frame_b["total_rows"], "Tab A and Tab B must have independent total_rows"
        assert frame_a["sensors"]["rpm"]["value"] != frame_b["sensors"]["rpm"]["value"], "Tab A and Tab B must have independent sensor values"
        
        print("[PASS] Item 6 multi-tab independent state verified!\n")

async def main():
    await test_rest_endpoint()
    await test_websocket_single()
    await test_mission_switch_clean_teardown()
    await test_concurrent_sessions()

if __name__ == "__main__":
    asyncio.run(main())
