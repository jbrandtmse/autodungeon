"""Autonomous autopilot monitor - checks every hour, generates 1-2 images, writes emergent behavior report."""
import json
import glob
import time
import datetime
import urllib.request
import urllib.error
import re
import os

LOG_FILE = "C:/autodungeon/monitor_log.txt"
REPORT_FILE = "C:/autodungeon/emergent_behavior_report.md"
CAMPAIGN_DIR = "C:/autodungeon/campaigns/session_009"
API_BASE = "http://localhost:8000/api"
GENERATED_TURNS = set()

# Track emergent behavior patterns across cycles
TRACKED_NPCS = set()
TRACKED_LOCATIONS = set()
TRACKED_ITEMS = set()
TRACKED_PLOT_THREADS = set()
CHARACTER_CATCHPHRASES = {
    "thorin": [], "brother aldric": [], "elara": [], "shadowmere": []
}
DEATH_SAVE_COUNT = 0
NATURAL_20_COUNT = 0
COMBAT_ENCOUNTERS = 0


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


STALL_COUNT = 0  # consecutive cycles with no new turns
LAST_ROUND_TIMES = []  # track round durations for performance monitoring


def api_post(path):
    try:
        req = urllib.request.Request(f"{API_BASE}{path}", method="POST",
                                     headers={"Content-Type": "application/json"}, data=b"")
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log(f"  API error on {path}: {e}")
        return None


def api_get(path):
    try:
        req = urllib.request.Request(f"{API_BASE}{path}", method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log(f"  API GET error on {path}: {e}")
        return None


def restart_servers():
    """Kill and restart FastAPI + SvelteKit servers."""
    import subprocess
    log("  >>> RESTARTING SERVERS <<<")

    # Kill existing uvicorn/node processes
    try:
        # Kill uvicorn
        subprocess.run(["taskkill", "/F", "/IM", "uvicorn.exe"], capture_output=True, timeout=10)
        subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq uvicorn*"],
                       capture_output=True, timeout=10)
        # Also try killing by port
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | "
             "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"],
            capture_output=True, timeout=15
        )
        log(f"  Killed processes on port 8000")
    except Exception as e:
        log(f"  Warning killing processes: {e}")

    time.sleep(5)

    # Restart FastAPI
    try:
        subprocess.Popen(
            ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd="C:/autodungeon",
            stdout=open("C:/autodungeon/server_restart.log", "a"),
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        log("  FastAPI server restarted")
    except Exception as e:
        log(f"  ERROR restarting FastAPI: {e}")
        return False

    # Wait for server to be ready
    for attempt in range(30):
        time.sleep(2)
        try:
            req = urllib.request.Request(f"{API_BASE}/sessions", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    log(f"  Server ready after {(attempt+1)*2}s")
                    return True
        except Exception:
            pass
    log("  Server did not become ready in 60s")
    return False


def restart_autopilot():
    """Reconnect via WebSocket and start autopilot."""
    log("  Attempting to restart autopilot via WebSocket...")
    try:
        import subprocess
        # Use a small Python script to send the WebSocket command
        ws_script = '''
import asyncio
import websockets
import json

async def start_autopilot():
    uri = "ws://localhost:8000/ws/game/009"
    async with websockets.connect(uri) as ws:
        # Wait for initial state
        msg = await asyncio.wait_for(ws.recv(), timeout=10)
        # Send start autopilot command
        await ws.send(json.dumps({"type": "start_autopilot", "speed": "fast"}))
        # Wait for acknowledgment
        msg = await asyncio.wait_for(ws.recv(), timeout=10)
        print(f"Autopilot response: {msg[:200]}")

asyncio.run(start_autopilot())
'''
        result = subprocess.run(
            ["python", "-c", ws_script],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            log(f"  Autopilot started: {result.stdout.strip()[:200]}")
            return True
        else:
            log(f"  Autopilot start failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        log(f"  ERROR restarting autopilot: {e}")
        return False


def get_latest_checkpoint():
    files = sorted(glob.glob(f"{CAMPAIGN_DIR}/turn_*.json"))
    if not files:
        return None, []
    latest = files[-1]
    with open(latest, "r") as f:
        data = json.load(f)
    return latest, data.get("ground_truth_log", [])


def find_interesting_turns(log_entries, last_seen_turn):
    candidates = []
    for i in range(last_seen_turn, len(log_entries)):
        entry = log_entries[i]
        if entry.startswith("[DM]:") and i not in GENERATED_TURNS:
            score = 0
            dramatic_words = ["erupts", "explodes", "charges", "strikes", "shatter",
                            "collapse", "fire", "light", "shadow", "blood", "scream",
                            "thunder", "blade", "magic", "barrier", "seal", "ancient",
                            "dragon", "beast", "monster", "giant", "demon", "undead",
                            "battle", "combat", "attack", "defend", "falls", "rises",
                            "tower", "chamber", "vault", "throne", "portal", "gate",
                            "sacrifice", "resurrection", "curse", "ritual", "beacon",
                            "spire", "darkness", "radiant", "silver", "emerald"]
            entry_lower = entry.lower()
            for word in dramatic_words:
                if word in entry_lower:
                    score += 1
            candidates.append((i, score, entry[:300]))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates


def analyze_emergent_behavior(log_entries, last_seen, current_total):
    """Analyze new turns for emergent behavior patterns."""
    global DEATH_SAVE_COUNT, NATURAL_20_COUNT, COMBAT_ENCOUNTERS

    findings = []
    new_entries = log_entries[last_seen:current_total]

    # --- NPC Detection ---
    npc_pattern = re.compile(r'\*\*([A-Z][a-z]+(?: [A-Z][a-z]+)*)\*\*')
    known_pcs = {"Thorin", "Brother Aldric", "Elara", "Shadowmere", "Valerius"}
    new_npcs = set()
    for entry in new_entries:
        if entry.startswith("[DM]:"):
            matches = npc_pattern.findall(entry)
            for m in matches:
                if m not in known_pcs and m not in TRACKED_NPCS and len(m) > 3:
                    new_npcs.add(m)
                    TRACKED_NPCS.add(m)
    if new_npcs:
        findings.append(f"**New NPCs introduced:** {', '.join(sorted(new_npcs))}")

    # --- Location Detection ---
    location_pattern = re.compile(r'(?:the |The )\*\*([A-Z][a-zA-Z\' ]+(?: of [a-zA-Z\' ]+)?)\*\*')
    new_locations = set()
    for entry in new_entries:
        if entry.startswith("[DM]:"):
            matches = location_pattern.findall(entry)
            for m in matches:
                clean = m.strip()
                if clean not in TRACKED_LOCATIONS and len(clean) > 4 and clean not in known_pcs:
                    new_locations.add(clean)
                    TRACKED_LOCATIONS.add(clean)
    if new_locations:
        findings.append(f"**New locations mentioned:** {', '.join(sorted(new_locations))}")

    # --- Item/Equipment Tracking ---
    new_items = set()
    for entry in new_entries:
        if entry.startswith("[SHEET]:"):
            item_match = re.findall(r'gained ([^;]+?)(?:;|$)', entry)
            for item in item_match:
                item = item.strip()
                if item and item not in TRACKED_ITEMS:
                    new_items.add(item)
                    TRACKED_ITEMS.add(item)
    if new_items:
        findings.append(f"**New equipment gained:** {', '.join(sorted(new_items))}")

    # --- Death Saves & Critical Moments ---
    for entry in new_entries:
        if "death save" in entry.lower() or "Death Save" in entry:
            DEATH_SAVE_COUNT += 1
        if "natural 20" in entry.lower() or "Natural 20" in entry or "Nat 20" in entry:
            NATURAL_20_COUNT += 1

    # --- Combat Detection ---
    for entry in new_entries:
        if entry.startswith("[DM]:"):
            combat_words = ["initiative", "combat begins", "attacks", "swings", "charges at",
                          "the battle", "roll for initiative", "combat encounter"]
            if any(w in entry.lower() for w in combat_words):
                COMBAT_ENCOUNTERS += 1

    # --- Character Catchphrase / Voice Tracking ---
    for entry in new_entries:
        for char in ["thorin", "brother aldric", "elara", "shadowmere"]:
            if entry.lower().startswith(f"[{char}]:"):
                quotes = re.findall(r'["\u201c]([^"\u201d]{10,80})["\u201d]', entry)
                for q in quotes[:1]:
                    CHARACTER_CATCHPHRASES[char].append(q)

    # --- Emergent Cooperation / Strategy ---
    cooperation_patterns = []
    for entry in new_entries:
        if not entry.startswith("[DM]:") and not entry.startswith("[SHEET]:"):
            for pc in ["Thorin", "Aldric", "Elara", "Shadowmere"]:
                speaker_match = re.match(r'\[([^\]]+)\]:', entry)
                if speaker_match:
                    speaker = speaker_match.group(1)
                    if pc.lower() not in speaker.lower() and pc in entry:
                        cooperation_patterns.append(f"{speaker} -> {pc}")

    if cooperation_patterns:
        coop_summary = {}
        for p in cooperation_patterns:
            coop_summary[p] = coop_summary.get(p, 0) + 1
        top_coop = sorted(coop_summary.items(), key=lambda x: x[1], reverse=True)[:5]
        findings.append(f"**Cross-character references:** {', '.join(f'{k} ({v}x)' for k,v in top_coop)}")

    # --- Plot Thread Emergence ---
    plot_keywords = ["prophecy", "curse", "betrayal", "alliance", "quest", "mission",
                    "spire", "beacon", "seal", "ritual", "gate", "key", "anchor",
                    "masters", "pale hand", "valerius", "blackwood", "old guard",
                    "corruption", "sacrifice", "source", "void", "guardian",
                    "relic", "tome", "sigil", "rune", "ward", "prison",
                    "warden", "commander", "archivist", "house of"]
    active_threads = set()
    for entry in new_entries:
        entry_lower = entry.lower()
        for kw in plot_keywords:
            if kw in entry_lower:
                active_threads.add(kw)
    new_threads = active_threads - TRACKED_PLOT_THREADS
    if new_threads:
        findings.append(f"**New plot threads:** {', '.join(sorted(new_threads))}")
        TRACKED_PLOT_THREADS.update(new_threads)
    if active_threads:
        findings.append(f"**Active plot threads this hour:** {', '.join(sorted(active_threads))}")

    # --- HP Trends ---
    hp_changes = []
    for entry in new_entries:
        if entry.startswith("[SHEET]:"):
            hp_match = re.search(r'HP: (\d+) -> (\d+)', entry)
            name_match = re.search(r'Updated ([^:]+):', entry)
            if hp_match and name_match:
                old_hp, new_hp = int(hp_match.group(1)), int(hp_match.group(2))
                name = name_match.group(1)
                hp_changes.append((name, old_hp, new_hp))
    if hp_changes:
        hp_summary = "; ".join(f"{n}: {o}->{new}" for n, o, new in hp_changes[-8:])
        findings.append(f"**HP changes:** {hp_summary}")

    # --- Skill Usage ---
    action_counts = {"stealth": 0, "attack": 0, "arcana": 0, "religion": 0,
                    "perception": 0, "medicine": 0, "athletics": 0, "investigation": 0,
                    "acrobatics": 0, "persuasion": 0, "insight": 0}
    for entry in new_entries:
        entry_lower = entry.lower()
        for action in action_counts:
            if f"using {action}" in entry_lower or f"using **{action}" in entry_lower:
                action_counts[action] += 1
    active_actions = {k: v for k, v in action_counts.items() if v > 0}
    if active_actions:
        findings.append(f"**Skill usage this hour:** {', '.join(f'{k}: {v}x' for k,v in sorted(active_actions.items(), key=lambda x: x[1], reverse=True))}")

    # --- Dice Roll Analysis ---
    rolls = []
    roll_pattern = re.compile(r'\[(\d+)\]')
    for entry in new_entries:
        if not entry.startswith("[DM]:") and not entry.startswith("[SHEET]:"):
            for match in roll_pattern.finditer(entry):
                val = int(match.group(1))
                if 1 <= val <= 20:
                    rolls.append(val)
    if rolls:
        avg_roll = sum(rolls) / len(rolls)
        crits = rolls.count(20)
        fumbles = rolls.count(1)
        findings.append(f"**Dice stats:** {len(rolls)} rolls, avg {avg_roll:.1f}, crits: {crits}, fumbles: {fumbles}")

    return findings


def write_report(cycle_num, total_turns, new_turns, findings, image_turns):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    header = f"\n## Hour {cycle_num} Report ({ts})\n\n"
    header += f"**Turns:** {total_turns - new_turns + 1} - {total_turns} ({new_turns} new turns)\n\n"

    if not findings:
        body = "_No notable emergent behavior detected this hour._\n"
    else:
        body = "### Emergent Behavior\n\n"
        for f in findings:
            body += f"- {f}\n"
        body += "\n"

    if image_turns:
        body += "### Images Generated\n\n"
        for turn_idx in image_turns:
            body += f"- Turn {turn_idx + 1}\n"
        body += "\n"

    body += "### Running Totals\n\n"
    body += f"| Metric | Value |\n|--------|-------|\n"
    body += f"| Total turns | {total_turns} |\n"
    body += f"| NPCs encountered | {len(TRACKED_NPCS)} |\n"
    body += f"| Locations discovered | {len(TRACKED_LOCATIONS)} |\n"
    body += f"| Items gained | {len(TRACKED_ITEMS)} |\n"
    body += f"| Death saves | {DEATH_SAVE_COUNT} |\n"
    body += f"| Natural 20s | {NATURAL_20_COUNT} |\n"
    body += f"| Combat encounters | {COMBAT_ENCOUNTERS} |\n"
    body += f"| Active plot threads | {len(TRACKED_PLOT_THREADS)} |\n"
    body += f"| Total images | {len(GENERATED_TURNS)} |\n"

    body += "\n### Notable Character Quotes\n\n"
    for char, quotes in CHARACTER_CATCHPHRASES.items():
        recent = quotes[-2:] if quotes else []
        if recent:
            for q in recent:
                body += f"- **{char.title()}:** \"{q}\"\n"
    if not any(CHARACTER_CATCHPHRASES.values()):
        body += "_No new quotes captured._\n"
    body += "\n---\n"

    with open(REPORT_FILE, "a") as f:
        f.write(header + body)

    log(f"  Report written to {REPORT_FILE}")


def check_server_health():
    """Check if the FastAPI server is responding."""
    try:
        req = urllib.request.Request(f"{API_BASE}/sessions", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def run_cycle(cycle_num, last_seen_turn):
    global STALL_COUNT
    log(f"=== Cycle {cycle_num}/12 ===")

    # Check server health first
    if not check_server_health():
        log("  Server is not responding! Attempting restart...")
        if restart_servers():
            time.sleep(10)
            restart_autopilot()
            STALL_COUNT = 0
        else:
            log("  Server restart failed. Will retry next cycle.")
            write_report(cycle_num, 0, 0,
                        ["**SERVER DOWN** - restart attempted but failed"], [])
            return last_seen_turn

    checkpoint_path, log_entries = get_latest_checkpoint()
    if not checkpoint_path:
        log("  No checkpoint found!")
        write_report(cycle_num, 0, 0, ["No checkpoint found - server may be down"], [])
        return last_seen_turn

    total_turns = len(log_entries)
    cp_name = os.path.basename(checkpoint_path)
    log(f"  Checkpoint: {cp_name}, Total turns: {total_turns}")

    if total_turns <= last_seen_turn:
        STALL_COUNT += 1
        log(f"  No new turns since last check (stall count: {STALL_COUNT})")

        if STALL_COUNT >= 2:
            log("  Autopilot appears stalled for 2+ hours. Restarting...")
            if restart_servers():
                time.sleep(10)
                restart_autopilot()
                STALL_COUNT = 0
            else:
                log("  Restart failed.")

        write_report(cycle_num, total_turns, 0,
                    [f"No new turns - stall count: {STALL_COUNT}. "
                     f"{'Restart attempted.' if STALL_COUNT >= 2 else 'Will check again next hour.'}"], [])
        return last_seen_turn

    # Reset stall counter on successful progress
    STALL_COUNT = 0

    new_turns = total_turns - last_seen_turn
    log(f"  New turns since last check: {new_turns}")

    # Check performance: turns per hour
    turns_per_hour = new_turns  # since we check every hour
    log(f"  Throughput: {turns_per_hour} turns/hour ({turns_per_hour/5:.1f} rounds/hour)")

    if turns_per_hour < 20 and cycle_num > 1:
        log(f"  WARNING: Low throughput ({turns_per_hour} turns/hr). Possible performance issue.")

    # Analyze emergent behavior
    findings = analyze_emergent_behavior(log_entries, last_seen_turn, total_turns)
    findings.insert(0, f"**Throughput:** {turns_per_hour} turns/hour ({turns_per_hour/5:.1f} rounds/hour)")
    for f in findings:
        log(f"  {f}")

    # Find interesting turns to illustrate
    candidates = find_interesting_turns(log_entries, last_seen_turn)
    image_turns = []

    if candidates:
        num_to_generate = min(2, len(candidates))
        selected = candidates[:num_to_generate]

        for turn_idx, score, preview in selected:
            log(f"  Generating image for Turn {turn_idx + 1} (score={score})")
            log(f"    Preview: {preview[:150]}...")
            result = api_post(f"/sessions/009/images/generate-turn/{turn_idx}")
            if result:
                log(f"    Queued: task_id={result.get('task_id', '?')}")
                GENERATED_TURNS.add(turn_idx)
                image_turns.append(turn_idx)
            time.sleep(5)
    else:
        log("  No strong illustration candidates found.")

    write_report(cycle_num, total_turns, new_turns, findings, image_turns)

    return total_turns


def main():
    log("=" * 60)
    log("AUTOPILOT MONITOR v2 - 12 hour run with emergent behavior tracking")
    log("=" * 60)

    # Initialize report file
    with open(REPORT_FILE, "w") as f:
        f.write("# Autodungeon Session 009 - Emergent Behavior Report Card\n\n")
        f.write(f"**Started:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Duration:** 12 hours (hourly checks)\n\n")
        f.write(f"**Session:** Race Gender Test (session_009)\n\n")
        f.write("This report tracks emergent AI behavior patterns including NPC creation, ")
        f.write("plot thread development, character cooperation, equipment progression, ")
        f.write("combat statistics, and narrative quality across a 12-hour autonomous play session.\n\n")
        f.write("---\n")

    # Initialize with current state
    _, initial_log = get_latest_checkpoint()
    last_seen = len(initial_log)
    log(f"Starting at turn {last_seen}")

    # Load already-generated image turns
    image_files = glob.glob(f"{CAMPAIGN_DIR}/images/*.json")
    for img_file in image_files:
        with open(img_file) as f:
            img_data = json.load(f)
            GENERATED_TURNS.add(img_data.get("turn_number", -1))
    log(f"Already generated images for turns: {sorted(GENERATED_TURNS)}")

    # Pre-scan existing log for baseline tracking
    if initial_log:
        _ = analyze_emergent_behavior(initial_log, 0, len(initial_log))
        log(f"Baseline scan: {len(TRACKED_NPCS)} NPCs, {len(TRACKED_LOCATIONS)} locations, "
            f"{len(TRACKED_PLOT_THREADS)} plot threads")
        # Keep only last 2 quotes per character from baseline
        for k in CHARACTER_CATCHPHRASES:
            CHARACTER_CATCHPHRASES[k] = CHARACTER_CATCHPHRASES[k][-2:]

    for cycle in range(1, 13):
        # Reset per-hour quote tracking
        for k in CHARACTER_CATCHPHRASES:
            CHARACTER_CATCHPHRASES[k] = []

        try:
            last_seen = run_cycle(cycle, last_seen)
        except Exception as e:
            log(f"  ERROR in cycle {cycle}: {e}")
            import traceback
            log(traceback.format_exc())

        if cycle < 12:
            log(f"  Sleeping 1 hour until next check...")
            time.sleep(3600)

    # Final summary
    log("=" * 60)
    log("AUTOPILOT MONITOR COMPLETE - 12 hours elapsed")
    log("=" * 60)

    _, final_log = get_latest_checkpoint()
    image_count = len(glob.glob(f"{CAMPAIGN_DIR}/images/*.png"))
    log(f"Final state: {len(final_log)} turns, {image_count} images generated")

    with open(REPORT_FILE, "a") as f:
        f.write(f"\n## Final Summary ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n")
        f.write(f"| Metric | Value |\n|--------|-------|\n")
        f.write(f"| Total turns played | {len(final_log)} |\n")
        f.write(f"| Total images generated | {image_count} |\n")
        f.write(f"| Unique NPCs | {len(TRACKED_NPCS)} |\n")
        f.write(f"| Unique locations | {len(TRACKED_LOCATIONS)} |\n")
        f.write(f"| Unique items | {len(TRACKED_ITEMS)} |\n")
        f.write(f"| Death saves | {DEATH_SAVE_COUNT} |\n")
        f.write(f"| Natural 20s | {NATURAL_20_COUNT} |\n")
        f.write(f"| Combat encounters | {COMBAT_ENCOUNTERS} |\n")
        f.write(f"\n**All plot threads:** {', '.join(sorted(TRACKED_PLOT_THREADS))}\n")
        f.write(f"\n**All NPCs:** {', '.join(sorted(TRACKED_NPCS))}\n")
        f.write(f"\n**All locations:** {', '.join(sorted(TRACKED_LOCATIONS))}\n")
        f.write(f"\n**All items:** {', '.join(sorted(TRACKED_ITEMS))}\n")


if __name__ == "__main__":
    main()
