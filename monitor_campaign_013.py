"""
Overnight monitoring script for Session 013 - The Great Modron March
1000-turn campaign with Tanis (Paladin), Kael (Ranger), Lyra (Bard), Nyx (Rogue)
DM: gemini-3-flash-preview, PCs: ollama/qwen3:30b

Monitors:
- Turn progress (logged every 50 turns)
- Combat encounters (checks for tactical mode - initiative, NPC turns)
- Errors and stalls
- Interesting narrative events
- Emergent behaviors

Run: python monitor_campaign_013.py
"""

import json
import glob
import os
import time
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

SESSION_DIR = Path("C:/autodungeon/campaigns/session_013")
LOG_FILE = Path("C:/autodungeon/campaign_013_monitor.log")
TARGET_TURNS = 1000
CHECK_INTERVAL = 300  # 5 minutes between checks
HOURLY_REPORT_INTERVAL = 3600  # 1 hour

# Track state across checks
last_turn_count = 0
last_hourly_report = 0
last_illustration_turn = 0
combat_encounters = []
interesting_events = []
stall_start = None
errors = []
first_combat_verified = False
ILLUSTRATION_INTERVAL = 25  # Generate an illustration every N turns
API_BASE = "http://localhost:8000/api"


def log(msg: str) -> None:
    """Write timestamped message to both console and log file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_latest_state() -> tuple[int, dict | None]:
    """Get the latest checkpoint turn number and state."""
    files = sorted(glob.glob(str(SESSION_DIR / "turn_*.json")))
    if not files:
        return 0, None
    latest = files[-1]
    turn_num = int(os.path.basename(latest).replace("turn_", "").replace(".json", ""))
    try:
        with open(latest, encoding="utf-8") as f:
            state = json.load(f)
        return turn_num, state
    except Exception as e:
        return turn_num, None


def check_for_combat(state: dict) -> dict | None:
    """Check if combat is active in the current state."""
    combat = state.get("combat_state")
    if combat and isinstance(combat, dict) and combat.get("active"):
        return combat
    return None


def analyze_log_entries(state: dict, since_turn: int) -> list[str]:
    """Analyze log entries for interesting events."""
    events = []
    log_entries = state.get("ground_truth_log", [])

    for i, entry in enumerate(log_entries):
        if i < since_turn:
            continue

        # Entries can be strings "[Agent]: content" or dicts with agent_name/content
        if isinstance(entry, dict):
            agent = entry.get("agent_name", "unknown")
            content = entry.get("content", "")
        elif isinstance(entry, str):
            # Parse "[Agent]: content" format
            m = re.match(r'\[([^\]]+)\]:\s*(.*)', entry, re.DOTALL)
            if m:
                agent = m.group(1)
                content = m.group(2)
            else:
                agent = "unknown"
                content = entry
        else:
            continue

        content_lower = content.lower()

        # Combat detection
        if any(kw in content_lower for kw in [
            "initiative", "roll for initiative", "combat begins",
            "draws weapon", "attacks", "sword", "spell attack",
            "damage", "hit points", "falls unconscious"
        ]):
            events.append(f"COMBAT INDICATOR (turn {i+1}, {agent}): {content[:150]}...")

        # Death/unconscious
        if any(kw in content_lower for kw in [
            "falls unconscious", "drops to 0", "death saving",
            "killed", "slain", "dies"
        ]):
            events.append(f"DEATH/DOWN (turn {i+1}, {agent}): {content[:150]}...")

        # Modron March specific events
        if any(kw in content_lower for kw in [
            "modron", "primus", "mechanus", "sigil", "portal",
            "plane", "outlands", "march", "rogue modron"
        ]):
            events.append(f"MODRON MARCH (turn {i+1}, {agent}): {content[:150]}...")

        # Character interactions and emergent behaviors
        if any(kw in content_lower for kw in [
            "trust", "betray", "secret", "whisper", "argue",
            "disagree", "alliance", "bond", "friendship",
            "sacrifice", "protect"
        ]):
            events.append(f"CHARACTER DYNAMIC (turn {i+1}, {agent}): {content[:150]}...")

        # Dice rolls
        rolls = re.findall(r'\((?:Athletics|Acrobatics|Perception|Stealth|Persuasion|Deception|Insight|Investigation|Arcana|Religion|Nature|History|Medicine|Survival|Performance|Intimidation|Animal Handling|Sleight of Hand):\s*\d+\)', content)
        if rolls:
            events.append(f"SKILL CHECK (turn {i+1}, {agent}): {', '.join(rolls)}")

    return events


def verify_tactical_combat(state: dict, combat: dict) -> str:
    """Verify if combat is running in tactical mode."""
    report_lines = ["=== TACTICAL COMBAT VERIFICATION ==="]

    # Check for initiative order (entries can be strings like "dm:npc_name" or dicts)
    initiative_order = combat.get("initiative_order", [])
    if initiative_order:
        report_lines.append(f"Initiative order found: {len(initiative_order)} combatants")
        for entry in initiative_order[:10]:
            if isinstance(entry, dict):
                name = entry.get("name", "?")
                init = entry.get("initiative", "?")
                is_npc = entry.get("is_npc", False)
                report_lines.append(f"  {'NPC' if is_npc else 'PC'}: {name} (initiative: {init})")
            elif isinstance(entry, str):
                tag = "NPC" if entry.startswith("dm:") else "PC"
                report_lines.append(f"  {tag}: {entry}")
    else:
        report_lines.append("WARNING: No initiative order found!")

    # Check for combat round
    current_round = combat.get("round_number", combat.get("current_round", 0))
    report_lines.append(f"Current combat round: {current_round}")

    # Check for NPC profiles
    npcs = combat.get("npc_profiles", combat.get("npc_combatants", {}))
    if npcs:
        report_lines.append(f"NPC combatants: {len(npcs)}")
        items = npcs.items() if isinstance(npcs, dict) else enumerate(npcs)
        for key, npc in list(items)[:5]:
            if isinstance(npc, dict):
                name = npc.get("name", str(key))
                hp_c = npc.get("hp_current", npc.get("hp", "?"))
                hp_m = npc.get("hp_max", "?")
                ac = npc.get("ac", "?")
                report_lines.append(f"  {name} (HP: {hp_c}/{hp_m}, AC: {ac})")
    else:
        report_lines.append("WARNING: No NPC combatants found!")

    # Check combat_mode in config
    game_config = state.get("game_config", {})
    combat_mode = game_config.get("combat_mode", state.get("combat_mode", "unknown"))
    report_lines.append(f"Combat mode setting: {combat_mode}")

    # Verdict
    is_tactical = bool(initiative_order) and current_round > 0
    if is_tactical:
        report_lines.append("VERDICT: Combat IS running in TACTICAL mode")
    else:
        report_lines.append("VERDICT: Combat may NOT be running in tactical mode - needs investigation")

    return "\n".join(report_lines)


def hourly_report(turn_count: int, state: dict, elapsed_hours: float) -> None:
    """Generate an hourly progress report."""
    log("=" * 60)
    log(f"HOURLY REPORT - {elapsed_hours:.1f} hours elapsed")
    log(f"  Turn count: {turn_count} / {TARGET_TURNS} ({turn_count/TARGET_TURNS*100:.1f}%)")

    if turn_count > 0 and elapsed_hours > 0:
        rate = turn_count / elapsed_hours
        remaining = TARGET_TURNS - turn_count
        eta_hours = remaining / rate if rate > 0 else float('inf')
        log(f"  Rate: {rate:.1f} turns/hour")
        log(f"  ETA to 1000: {eta_hours:.1f} hours")

    if state:
        # Character count
        chars = state.get("characters", {})
        log(f"  Characters: {list(chars.keys())}")

        # Memory stats
        memories = state.get("agent_memories", {})
        for name, mem in memories.items():
            if isinstance(mem, dict):
                buffer_len = len(mem.get("short_term_buffer", []))
                has_summary = bool(mem.get("long_term_summary"))
                log(f"  Memory [{name}]: buffer={buffer_len}, has_summary={has_summary}")

        # Combat state
        combat = check_for_combat(state)
        if combat:
            log(f"  COMBAT ACTIVE: round {combat.get('current_round', '?')}")

    log(f"  Combat encounters so far: {len(combat_encounters)}")
    log(f"  Interesting events logged: {len(interesting_events)}")
    log(f"  Errors: {len(errors)}")
    log("=" * 60)


def generate_illustration(turn_number: int) -> bool:
    """Generate an illustration for a specific turn via the API."""
    url = f"{API_BASE}/sessions/013/images/generate-turn/{turn_number}"
    try:
        req = urllib.request.Request(url, method="POST", data=b"",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            task_id = result.get("task_id", "?")
            log(f"  Illustration requested for turn {turn_number + 1} (task: {task_id})")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        log(f"  Illustration FAILED for turn {turn_number + 1}: HTTP {e.code} - {body}")
        return False
    except Exception as e:
        log(f"  Illustration FAILED for turn {turn_number + 1}: {e}")
        return False


def main():
    global last_turn_count, last_hourly_report, last_illustration_turn, stall_start, first_combat_verified

    log("=" * 60)
    log("CAMPAIGN 013 MONITOR STARTED")
    log(f"Session: The Great Modron March")
    log(f"Party: Tanis (Paladin), Kael (Ranger), Lyra (Bard), Nyx (Rogue)")
    log(f"DM: gemini-3-flash-preview | PCs: ollama/qwen3:30b")
    log(f"Target: {TARGET_TURNS} turns")
    log(f"Check interval: {CHECK_INTERVAL}s")
    log("=" * 60)

    start_time = time.time()
    last_hourly_report = start_time

    while True:
        try:
            turn_count, state = get_latest_state()

            # Progress tracking
            if turn_count > last_turn_count:
                delta = turn_count - last_turn_count
                log(f"Progress: turn {turn_count} (+{delta} since last check)")

                # Reset stall tracker
                stall_start = None

                # Analyze new entries
                if state:
                    new_events = analyze_log_entries(state, last_turn_count)
                    for event in new_events:
                        log(f"  EVENT: {event}")
                        interesting_events.append(event)

                    # Check for combat
                    combat = check_for_combat(state)
                    if combat and not first_combat_verified:
                        log("FIRST COMBAT DETECTED! Verifying tactical mode...")
                        report = verify_tactical_combat(state, combat)
                        log(report)
                        first_combat_verified = True
                        combat_encounters.append({
                            "turn": turn_count,
                            "report": report
                        })
                    elif combat:
                        round_num = combat.get("current_round", 0)
                        log(f"  Combat active: round {round_num}")
                        combat_encounters.append({
                            "turn": turn_count,
                            "round": round_num
                        })

                # Milestone logging
                if turn_count % 50 == 0 or turn_count in [10, 25]:
                    elapsed = (time.time() - start_time) / 3600
                    rate = turn_count / elapsed if elapsed > 0 else 0
                    log(f"MILESTONE: Turn {turn_count} reached ({rate:.1f} turns/hr)")

                # Periodic illustrations (every ~25 turns)
                if turn_count - last_illustration_turn >= ILLUSTRATION_INTERVAL and turn_count >= 5:
                    log(f"Generating illustration at turn {turn_count}...")
                    # Illustrate a turn slightly before current (more complete scene)
                    illustrate_turn = max(0, turn_count - 3)
                    if generate_illustration(illustrate_turn):
                        last_illustration_turn = turn_count

                last_turn_count = turn_count

            elif turn_count == last_turn_count and last_turn_count > 0:
                # Potential stall
                if stall_start is None:
                    stall_start = time.time()
                else:
                    stall_duration = time.time() - stall_start
                    if stall_duration > 600:  # 10 minutes
                        log(f"WARNING: Stall detected! No progress for {stall_duration/60:.1f} minutes at turn {turn_count}")
                        errors.append(f"Stall at turn {turn_count} for {stall_duration/60:.1f} min")

            # Hourly report
            if time.time() - last_hourly_report >= HOURLY_REPORT_INTERVAL:
                elapsed_hours = (time.time() - start_time) / 3600
                if state:
                    hourly_report(turn_count, state, elapsed_hours)
                last_hourly_report = time.time()

            # Target reached?
            if turn_count >= TARGET_TURNS:
                log(f"TARGET REACHED: {turn_count} turns!")
                elapsed = (time.time() - start_time) / 3600
                log(f"Total time: {elapsed:.1f} hours")
                log(f"Average rate: {turn_count/elapsed:.1f} turns/hour")
                break

        except KeyboardInterrupt:
            log("Monitor stopped by user")
            break
        except Exception as e:
            log(f"ERROR: {e}")
            errors.append(str(e))

        time.sleep(CHECK_INTERVAL)

    # Final report
    log("\n" + "=" * 60)
    log("FINAL MONITOR REPORT")
    log(f"Total turns: {last_turn_count}")
    log(f"Combat encounters: {len(combat_encounters)}")
    log(f"Interesting events: {len(interesting_events)}")
    log(f"Errors: {len(errors)}")
    if combat_encounters:
        log("\nCombat encounters:")
        for c in combat_encounters:
            log(f"  Turn {c.get('turn', '?')}: {c.get('report', c.get('round', ''))[:100]}")
    log("=" * 60)


if __name__ == "__main__":
    main()
