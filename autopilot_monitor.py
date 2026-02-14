"""Resilient autopilot monitor - keeps autopilot running and restarts on stall."""

import asyncio
import json
import time
import websockets


async def monitor_autopilot(
    session_id: str = "008",
    speed: str = "fast",
    check_interval: int = 60,
    stall_threshold: int = 660,
):
    """Monitor autopilot and restart it if it stalls.

    Note: stall_threshold must be longer than the longest expected round.
    A full round (context_manager + DM on Gemini + 4 PCs on Ollama) can
    take 3-5 minutes. Setting threshold too low kills healthy rounds and
    orphans threads that keep running in the background.

    Args:
        session_id: Game session to monitor.
        speed: Autopilot speed setting.
        check_interval: Seconds between health checks.
        stall_threshold: Seconds without activity before restarting.
    """
    uri = f"ws://localhost:8000/ws/game/{session_id}"
    last_turn = 0
    last_turn_time = time.time()
    last_activity_time = time.time()  # Any activity (turns, retries, heartbeats)
    restart_count = 0

    while True:
        try:
            async with websockets.connect(uri, max_size=50 * 1024 * 1024) as ws:
                # Read initial state
                raw = await asyncio.wait_for(ws.recv(), timeout=15)
                state = json.loads(raw)
                current_turn = state.get("state", {}).get("turn_number", 0)
                print(f"[{time.strftime('%H:%M:%S')}] Connected. Turn: {current_turn}")

                if current_turn > last_turn:
                    last_turn = current_turn
                    last_turn_time = time.time()
                last_activity_time = time.time()

                # Start autopilot
                await ws.send(json.dumps({"type": "set_speed", "speed": speed}))
                await ws.send(json.dumps({"type": "start_autopilot", "speed": speed}))

                # Read response
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5)
                    resp = json.loads(raw)
                    if resp.get("type") == "error":
                        msg = resp.get("message", "")
                        if "already running" in msg.lower():
                            print(f"[{time.strftime('%H:%M:%S')}] Autopilot already running")
                        else:
                            print(f"[{time.strftime('%H:%M:%S')}] Error: {msg}")
                    elif resp.get("type") == "autopilot_started":
                        restart_count += 1
                        print(
                            f"[{time.strftime('%H:%M:%S')}] Autopilot started "
                            f"(restart #{restart_count})"
                        )
                except asyncio.TimeoutError:
                    pass

                # Monitor loop - listen for events
                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=check_interval)
                        event = json.loads(raw)
                        event_type = event.get("type", "")

                        if event_type == "turn_update":
                            turn = event.get("turn", 0)
                            agent = event.get("agent", "?")
                            if turn > last_turn:
                                last_turn = turn
                                last_turn_time = time.time()
                                last_activity_time = time.time()
                                print(
                                    f"[{time.strftime('%H:%M:%S')}] "
                                    f"Turn {turn} [{agent}]"
                                )

                        elif event_type == "autopilot_retry":
                            # Engine is retrying after error - it's alive, reset activity
                            attempt = event.get("attempt", "?")
                            max_attempts = event.get("max_attempts", "?")
                            backoff = event.get("backoff_seconds", "?")
                            error = event.get("error", "")
                            last_activity_time = time.time()
                            print(
                                f"[{time.strftime('%H:%M:%S')}] "
                                f"Retry {attempt}/{max_attempts} "
                                f"(backoff {backoff}s): {error}"
                            )

                        elif event_type == "autopilot_heartbeat":
                            # Engine is alive during backoff
                            last_activity_time = time.time()
                            remaining = event.get("remaining_seconds", "?")
                            status = event.get("status", "?")
                            print(
                                f"[{time.strftime('%H:%M:%S')}] "
                                f"Heartbeat: {status}, {remaining}s remaining"
                            )

                        elif event_type == "autopilot_stopped":
                            reason = event.get("reason", "unknown")
                            print(
                                f"[{time.strftime('%H:%M:%S')}] "
                                f"Autopilot stopped: {reason}. Restarting in 10s..."
                            )
                            await asyncio.sleep(10)
                            await ws.send(
                                json.dumps({"type": "start_autopilot", "speed": speed})
                            )
                            last_activity_time = time.time()

                        elif event_type == "error":
                            last_activity_time = time.time()
                            print(
                                f"[{time.strftime('%H:%M:%S')}] "
                                f"Error: {event.get('message', '')}"
                            )

                    except asyncio.TimeoutError:
                        # Check for stall using activity time (includes retries/heartbeats)
                        turn_elapsed = time.time() - last_turn_time
                        activity_elapsed = time.time() - last_activity_time
                        if activity_elapsed > stall_threshold:
                            print(
                                f"[{time.strftime('%H:%M:%S')}] "
                                f"Stall detected: no activity for {activity_elapsed:.0f}s "
                                f"(last turn {turn_elapsed:.0f}s ago). Restarting..."
                            )
                            # Stop autopilot and wait for confirmation
                            await ws.send(json.dumps({"type": "stop_autopilot"}))
                            # Wait up to 30s for stop confirmation
                            stop_confirmed = False
                            try:
                                for _ in range(6):  # 6 x 5s = 30s max
                                    raw = await asyncio.wait_for(ws.recv(), timeout=5)
                                    resp = json.loads(raw)
                                    if resp.get("type") == "autopilot_stopped":
                                        stop_confirmed = True
                                        break
                            except asyncio.TimeoutError:
                                pass
                            if not stop_confirmed:
                                print(
                                    f"[{time.strftime('%H:%M:%S')}] "
                                    f"Stop not confirmed after 30s, forcing restart..."
                                )
                            else:
                                print(
                                    f"[{time.strftime('%H:%M:%S')}] "
                                    f"Stop confirmed, restarting after 5s..."
                                )
                            await asyncio.sleep(5)
                            await ws.send(
                                json.dumps({"type": "start_autopilot", "speed": speed})
                            )
                            last_activity_time = time.time()
                            last_turn_time = time.time()
                        else:
                            print(
                                f"[{time.strftime('%H:%M:%S')}] "
                                f"Heartbeat: Turn {last_turn}, "
                                f"idle {turn_elapsed:.0f}s, "
                                f"activity {activity_elapsed:.0f}s ago"
                            )

        except (websockets.ConnectionClosed, OSError) as e:
            print(
                f"[{time.strftime('%H:%M:%S')}] Connection lost: {e}. "
                f"Reconnecting in 15s..."
            )
            await asyncio.sleep(15)
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Unexpected error: {e}. Retrying in 30s...")
            await asyncio.sleep(30)


if __name__ == "__main__":
    print("=== Autopilot Monitor ===")
    print("Session: 008, Speed: fast")
    print("Stall threshold: 11 min, Check interval: 60s")
    print("Press Ctrl+C to stop\n")
    asyncio.run(monitor_autopilot())
