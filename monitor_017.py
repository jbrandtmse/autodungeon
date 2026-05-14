"""Monitor session 017: generate images every 20 turns, stop autopilot at turn 100."""

import asyncio
import json
import time

import requests
import websockets

SESSION = "017"
BASE = "http://localhost:8000"
WS_URL = f"ws://localhost:8000/ws/game/{SESSION}"
IMAGE_EVERY = 20
STOP_AT = 100
POLL_INTERVAL = 30  # seconds between turn-count checks


def get_turn_count() -> int:
    try:
        r = requests.get(f"{BASE}/api/sessions/{SESSION}", timeout=10)
        r.raise_for_status()
        return r.json().get("turn_count", 0)
    except Exception as e:
        print(f"  [warn] Could not get turn count: {e}")
        return -1


def generate_image(turn: int) -> None:
    print(f"  [img] Requesting image for turn {turn} ...")
    try:
        r = requests.post(
            f"{BASE}/api/sessions/{SESSION}/images/generate-best",
            timeout=15,
        )
        if r.ok:
            print(f"  [img] Image generation queued: {r.json()}")
        else:
            print(f"  [img] Image request failed {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  [img] Error requesting image: {e}")


async def stop_autopilot() -> None:
    print("  [stop] Sending stop_autopilot via WebSocket ...")
    try:
        async with websockets.connect(WS_URL, open_timeout=10) as ws:
            await ws.send(json.dumps({"type": "stop_autopilot"}))
            # Wait briefly for ack
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"  [stop] Response: {msg}")
            except asyncio.TimeoutError:
                print("  [stop] No ack received (timeout) — stop sent.")
    except Exception as e:
        print(f"  [stop] WebSocket error: {e}")


def main() -> None:
    print(f"Monitor started — session {SESSION}")
    print(f"  Images every {IMAGE_EVERY} turns, stop at {STOP_AT}")

    last_image_milestone = 0
    stopped = False

    while not stopped:
        turns = get_turn_count()
        print(f"[{time.strftime('%H:%M:%S')}] Turn count: {turns}")

        if turns >= STOP_AT and not stopped:
            generate_image(turns)
            asyncio.run(stop_autopilot())
            print(f"Autopilot stopped at turn {turns}. Done!")
            stopped = True
            break

        # Generate image at each milestone (20, 40, 60, 80)
        milestone = (turns // IMAGE_EVERY) * IMAGE_EVERY
        if milestone > 0 and milestone > last_image_milestone:
            generate_image(turns)
            last_image_milestone = milestone

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
