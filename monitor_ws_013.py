"""
WebSocket-based overnight monitor for Session 013.
Connects via Vite proxy, starts autopilot, monitors progress,
auto-restarts on failure, and generates illustrations periodically.

Run: python monitor_ws_013.py
"""

import asyncio
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# We use the websockets library for the async WS client
try:
    import websockets
except ImportError:
    print("ERROR: websockets library required. Install with: pip install websockets")
    raise SystemExit(1)

WS_URI = "ws://localhost:5173/ws/game/013"
API_BASE = "http://localhost:8000/api"
LOG_FILE = Path("C:/autodungeon/campaign_013_ws_monitor.log")
TARGET_TURNS = 1000
ILLUSTRATION_INTERVAL = 25  # Every N turns

# State tracking
last_turn = 0
last_illustration_turn = 0
autopilot_restarts = 0
total_errors = 0
start_time = 0.0


def log(msg: str) -> None:
    """Write timestamped message to console and log file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def generate_illustration(turn_number: int) -> bool:
    """Generate an illustration for a specific turn via the REST API."""
    # Use turn index (0-based) for the API
    turn_idx = max(0, turn_number - 3)
    url = f"{API_BASE}/sessions/013/images/generate-turn/{turn_idx}"
    try:
        req = urllib.request.Request(url, method="POST", data=b"",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            task_id = result.get("task_id", "?")
            log(f"  Illustration requested for turn {turn_number} (task: {task_id})")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        log(f"  Illustration FAILED for turn {turn_number}: HTTP {e.code} - {body}")
        return False
    except Exception as e:
        log(f"  Illustration FAILED for turn {turn_number}: {e}")
        return False


async def run_monitor():
    """Main monitor loop with auto-reconnect and auto-restart."""
    global last_turn, last_illustration_turn, autopilot_restarts, total_errors, start_time

    start_time = time.time()
    last_hourly_report = start_time

    log("=" * 60)
    log("SESSION 013 WS MONITOR STARTED")
    log(f"Target: {TARGET_TURNS} turns")
    log(f"Illustration interval: every {ILLUSTRATION_INTERVAL} turns")
    log("=" * 60)

    while last_turn < TARGET_TURNS:
        try:
            log(f"Connecting to {WS_URI}...")
            async with websockets.connect(WS_URI, ping_interval=30, ping_timeout=60,
                                           close_timeout=10) as ws:
                log("Connected!")

                # Get initial state
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)
                    data = json.loads(msg)
                    if data.get("type") == "session_state":
                        state = data.get("state", {})
                        last_turn = state.get("turn_number", last_turn)
                        current = state.get("current_turn", "?")
                        log(f"Session state: turn {last_turn}, current_turn={current}")
                except asyncio.TimeoutError:
                    log("No initial state received, continuing...")

                # Start autopilot
                await ws.send(json.dumps({"type": "start_autopilot", "speed": "normal"}))
                log("Autopilot START sent")

                # Monitor loop
                consecutive_silence = 0
                while True:
                    try:
                        # Wait for message (up to 120s per message - generous for slow rounds)
                        msg = await asyncio.wait_for(ws.recv(), timeout=120)
                        data = json.loads(msg)
                        msg_type = data.get("type", "?")
                        consecutive_silence = 0

                        if msg_type == "turn_update":
                            turn = data.get("turn", "?")
                            agent = data.get("agent", "?")
                            last_turn = turn if isinstance(turn, int) else last_turn
                            elapsed = (time.time() - start_time) / 3600
                            rate = last_turn / elapsed if elapsed > 0 else 0
                            log(f"TURN {turn} [{agent}] ({rate:.0f} turns/hr)")

                            # Milestone logging
                            if isinstance(turn, int) and turn % 50 == 0:
                                remaining = TARGET_TURNS - turn
                                eta = remaining / rate if rate > 0 else float('inf')
                                log(f"  MILESTONE: {turn}/{TARGET_TURNS} "
                                    f"({turn/TARGET_TURNS*100:.0f}%) "
                                    f"ETA: {eta:.1f} hrs")

                            # Illustrations
                            if isinstance(turn, int) and turn - last_illustration_turn >= ILLUSTRATION_INTERVAL:
                                log(f"Generating illustration at turn {turn}...")
                                if generate_illustration(turn):
                                    last_illustration_turn = turn

                        elif msg_type == "autopilot_started":
                            log("Autopilot STARTED")

                        elif msg_type == "autopilot_stopped":
                            reason = data.get("reason", "unknown")
                            log(f"Autopilot STOPPED: {reason}")
                            if reason == "turn_limit":
                                log("Turn limit reached, restarting autopilot...")
                                await asyncio.sleep(2)
                                await ws.send(json.dumps({"type": "start_autopilot", "speed": "normal"}))
                                autopilot_restarts += 1
                                log(f"Autopilot RESTART #{autopilot_restarts}")
                            elif reason == "error":
                                total_errors += 1
                                log(f"Error stop (total errors: {total_errors}), "
                                    f"waiting 30s then restarting...")
                                await asyncio.sleep(30)
                                await ws.send(json.dumps({"type": "start_autopilot", "speed": "normal"}))
                                autopilot_restarts += 1
                                log(f"Autopilot RESTART #{autopilot_restarts} after error")
                            else:
                                log(f"Unexpected stop reason: {reason}, "
                                    f"waiting 10s then restarting...")
                                await asyncio.sleep(10)
                                await ws.send(json.dumps({"type": "start_autopilot", "speed": "normal"}))
                                autopilot_restarts += 1

                        elif msg_type == "autopilot_retry":
                            attempt = data.get("attempt", "?")
                            max_attempts = data.get("max_attempts", "?")
                            backoff = data.get("backoff_seconds", "?")
                            error_msg = data.get("error", "?")
                            log(f"Autopilot RETRY {attempt}/{max_attempts} "
                                f"(backoff {backoff}s): {str(error_msg)[:200]}")

                        elif msg_type == "autopilot_heartbeat":
                            status = data.get("status", "?")
                            remaining = data.get("remaining_seconds", "?")
                            log(f"  heartbeat: {status} ({remaining}s remaining)")

                        elif msg_type == "error":
                            error_msg = data.get("message", "unknown")
                            recoverable = data.get("recoverable", False)
                            total_errors += 1
                            log(f"ERROR: {error_msg} "
                                f"(recoverable={recoverable}, total={total_errors})")

                        elif msg_type == "session_state":
                            # Update state on reconnect
                            state = data.get("state", {})
                            last_turn = state.get("turn_number", last_turn)

                        elif msg_type == "image_generation_complete":
                            image_id = data.get("image_id", "?")
                            log(f"  Image generated: {image_id}")

                        elif msg_type == "image_generation_error":
                            error_msg = data.get("message", "?")
                            log(f"  Image error: {error_msg}")

                        # Skip other message types silently

                    except asyncio.TimeoutError:
                        consecutive_silence += 1
                        log(f"No message for 120s (silence count: {consecutive_silence})")
                        if consecutive_silence >= 5:  # 10 min of silence
                            log("Extended silence - reconnecting...")
                            break

                    # Hourly report
                    if time.time() - last_hourly_report >= 3600:
                        elapsed = (time.time() - start_time) / 3600
                        rate = last_turn / elapsed if elapsed > 0 else 0
                        remaining = TARGET_TURNS - last_turn
                        eta = remaining / rate if rate > 0 else float('inf')
                        log("=" * 50)
                        log(f"HOURLY REPORT - {elapsed:.1f} hours elapsed")
                        log(f"  Turn: {last_turn}/{TARGET_TURNS} ({last_turn/TARGET_TURNS*100:.0f}%)")
                        log(f"  Rate: {rate:.0f} turns/hr")
                        log(f"  ETA: {eta:.1f} hrs")
                        log(f"  Restarts: {autopilot_restarts}")
                        log(f"  Total errors: {total_errors}")
                        log("=" * 50)
                        last_hourly_report = time.time()

                    # Check target
                    if last_turn >= TARGET_TURNS:
                        log(f"TARGET REACHED: {last_turn} turns!")
                        break

        except websockets.exceptions.ConnectionClosed as e:
            log(f"WebSocket closed: {e}. Reconnecting in 10s...")
            await asyncio.sleep(10)
        except ConnectionRefusedError:
            log("Connection refused. Server may be down. Retrying in 30s...")
            await asyncio.sleep(30)
        except Exception as e:
            log(f"Unexpected error: {e}. Reconnecting in 15s...")
            await asyncio.sleep(15)

    # Final report
    elapsed = (time.time() - start_time) / 3600
    log("\n" + "=" * 60)
    log("FINAL MONITOR REPORT")
    log(f"  Total turns: {last_turn}")
    log(f"  Elapsed: {elapsed:.1f} hours")
    log(f"  Average rate: {last_turn / elapsed:.0f} turns/hr" if elapsed > 0 else "  N/A")
    log(f"  Autopilot restarts: {autopilot_restarts}")
    log(f"  Total errors: {total_errors}")
    log("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_monitor())
