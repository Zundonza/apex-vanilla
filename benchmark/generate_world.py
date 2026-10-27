"""
Benchmark Torture Chamber World Generator (PERMANENT SUSTAINED HEAVY LOAD)
Creates an unrelenting stress world where entities cannot die and hoppers never sleep:
- Sector 1: 500 Villagers + 150 Zombies separated by Iron Bars (Perpetual, unending A* pathfinding and panic)
- Sector 2: 3,500 Hoppers with 500 Items circulating over Packed Ice canals (Never-ending raycast scans)
- Sector 3: 80 High-Frequency Observer Clocks & 120 Piston-Redstone Blocks (Perpetual block & light updates)
- Sector 4: 2,000 Cows in 10 Water Stampede Pens (Massive O(N^2) continuous collision push calculations)
- Sector 5: 80 Minecarts constantly speeding on Rail Loops
"""

import sys
import os
import shutil
import time
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT_DIR / "run"
WORLD_DIR = RUN_DIR / "world"
TEMPLATE_DIR = ROOT_DIR / "benchmark" / "world-template"

def get_java_exe() -> str:
    candidates = [
        Path(r"D:\jdks\jdk-28\bin\java.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "java"

def create_datapack():
    dp_dir = WORLD_DIR / "datapacks" / "torture"
    functions_dir = dp_dir / "data" / "benchmark" / "function"
    tags_dir = dp_dir / "data" / "minecraft" / "tags" / "function"
    functions_dir.mkdir(parents=True, exist_ok=True)
    tags_dir.mkdir(parents=True, exist_ok=True)

    mcmeta = {
        "pack": {
            "pack_format": 61,
            "description": "Benchmark Permanent Extreme Torture Generator"
        }
    }
    with open(dp_dir / "pack.mcmeta", "w", encoding="utf-8") as f:
        json_str = str(mcmeta).replace("'", '"')
        f.write(json_str)

    load_tag = {"values": ["benchmark:build"]}
    with open(tags_dir / "load.json", "w", encoding="utf-8") as f:
        f.write(str(load_tag).replace("'", '"'))

    BY = -7 # Surface level on flat world

    lines = [
        "# Benchmark Initial Setup",
        "gamerule advance_time false",
        "gamerule advance_weather false",
        "gamerule spawn_mobs false",
        "gamerule spawn_monsters false",
        "gamerule random_tick_speed 0",
        "time set noon",
        "forceload add -8 -8 16 16",
        ""
    ]

    # --- SECTOR 1: 500 Villagers + 150 Zombies (Separated by Iron Bars - UNENDING PATHFINDING) ---
    lines.append(f"# --- Sector 1: Perpetual Pathfinding Arena (Y={BY}) ---")
    lines.append(f"fill -60 {BY} -60 0 {BY+4} 0 minecraft:barrier hollow")
    lines.append(f"fill -59 {BY} -59 -1 {BY} -1 minecraft:smooth_stone")
    
    # Iron bars barrier right down the middle so zombies can see but never reach/kill villagers
    lines.append(f"fill -60 {BY+1} -30 0 {BY+3} -30 minecraft:iron_bars")
    
    # 500 Villagers in Zone A (-60..0, -29..-1)
    for i in range(500):
        vx = -55 + (i % 50)
        vz = -28 + ((i // 50) * 3 % 26)
        lines.append(f"summon minecraft:villager {vx}.5 {BY+1}.1 {vz}.5 {{PersistenceRequired:1b,NoAI:0b}}")
    
    # 150 Zombies in Zone B (-60..0, -59..-31)
    for z in range(150):
        zx = -55 + (z % 50)
        zz = -35 - ((z // 50) * 3 % 20)
        lines.append(f"summon minecraft:zombie {zx}.5 {BY+1}.1 {zz}.5 {{PersistenceRequired:1b}}")
    lines.append("")

    # --- SECTOR 2: 3,500 Full Hoppers + 400 Floating Items on Ice Streams ---
    lines.append(f"# --- Sector 2: 3,500 Hoppers with Continuous Items (Y={BY}) ---")
    lines.append(f"fill 10 {BY} 0 44 {BY} 49 minecraft:hopper[facing=east]")
    lines.append(f"fill 10 {BY+1} 0 44 {BY+1} 49 minecraft:hopper[facing=south]")
    lines.append(f"fill 10 {BY+2} 0 44 {BY+2} 49 minecraft:hopper[facing=west]")
    
    # Ice stream canal above hoppers with water flow
    lines.append(f"fill 10 {BY+3} 0 44 {BY+3} 49 minecraft:packed_ice")
    lines.append(f"fill 10 {BY+4} 0 44 {BY+4} 0 minecraft:water")
    for ix in range(12, 42, 2):
        for iz in range(2, 48, 3):
            lines.append(f"summon minecraft:item {ix}.5 {BY+4}.5 {iz}.5 {{Item:{{id:\"minecraft:cobblestone\",count:1b}},Age:-32768s}}")
    lines.append("")

    # --- SECTOR 3: 80 Observer Clocks + Pistons & Lamps (Redstone Engine) ---
    lines.append(f"# --- Sector 3: 80 Observer Clocks ---")
    for r in range(80):
        rz = r * 2
        lines.append(f"setblock 60 {BY+1} {rz} minecraft:observer[facing=west]")
        lines.append(f"setblock 59 {BY+1} {rz} minecraft:observer[facing=east]")
        lines.append(f"fill 61 {BY+1} {rz} 75 {BY+1} {rz} minecraft:redstone_wire")
        lines.append(f"setblock 76 {BY+1} {rz} minecraft:sticky_piston[facing=up]")
        lines.append(f"setblock 76 {BY+2} {rz} minecraft:redstone_block")
        lines.append(f"fill 77 {BY+1} {rz} 85 {BY+1} {rz} minecraft:redstone_lamp")
    lines.append("")

    # --- SECTOR 4: 2,000 Packed Cows in 10 Water Stampede Pens ---
    lines.append(f"# --- Sector 4: 2,000 Packed Cows Stampede ---")
    pens = [
        (-10, 10), (-15, 10), (-20, 10), (-25, 10), (-30, 10),
        (-10, 15), (-15, 15), (-20, 15), (-25, 15), (-30, 15)
    ]
    for px, pz in pens:
        lines.append(f"fill {px-1} {BY+1} {pz-1} {px+2} {BY+4} {pz+2} minecraft:glass hollow")
        lines.append(f"setblock {px} {BY+1} {pz} minecraft:water")
        lines.append(f"setblock {px+1} {BY+1} {pz+1} minecraft:water")
        for _ in range(200): # 200 * 10 = 2,000 cows!
            lines.append(f"summon minecraft:cow {px}.5 {BY+1}.2 {pz}.5 {{PersistenceRequired:1b}}")
    lines.append("")

    # --- SECTOR 5: 80 Hopper Minecarts on Speed Loops ---
    lines.append(f"# --- Sector 5: 80 Hopper Minecarts ---")
    for m in range(40):
        mz = m * 2
        lines.append(f"fill 90 {BY+1} {mz} 105 {BY+1} {mz} minecraft:powered_rail")
        lines.append(f"setblock 89 {BY+1} {mz} minecraft:redstone_block")
        lines.append(f"summon minecraft:hopper_minecart 95.5 {BY+1}.5 {mz}.5")
        lines.append(f"summon minecraft:hopper_minecart 98.5 {BY+1}.5 {mz}.5")
    lines.append("")

    lines.append('say [BENCHMARK_SETUP_COMPLETE]')

    with open(functions_dir / "build.mcfunction", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[benchmark] Permanent Extreme Datapack generated at {dp_dir}")

def generate():
    if not (RUN_DIR / "server.jar").exists():
        print(f"[benchmark] Error: {RUN_DIR / 'server.jar'} does not exist. Run build-jar first.")
        sys.exit(1)

    print("[benchmark] Preparing permanent extreme run environment...")
    if WORLD_DIR.exists():
        shutil.rmtree(WORLD_DIR)
    WORLD_DIR.mkdir(parents=True, exist_ok=True)

    create_datapack()

    java_bin = get_java_exe()
    print(f"[benchmark] Starting server using {java_bin} in headless mode to generate world...")
    cmd = [java_bin, "-Xmx4G", "-Xms4G", "-jar", "server.jar", "--nogui"]
    proc = subprocess.Popen(
        cmd,
        cwd=RUN_DIR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    setup_finished = False
    start_time = time.time()
    
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        clean = line.strip()
        if any(k in clean for k in ["Done (", "BENCHMARK", "Starting", "Saving"]):
            print(f"  [server] {clean}", flush=True)
            
        if "[BENCHMARK_SETUP_COMPLETE]" in clean:
            setup_finished = True
            print("[benchmark] Permanent extreme world generation complete! Stopping server...", flush=True)
            proc.stdin.write("stop\n")
            proc.stdin.flush()
            break
        if time.time() - start_time > 360:
            print("[benchmark] Timeout waiting for world generation!", flush=True)
            proc.kill()
            break

    proc.wait()
    print("[benchmark] Server stopped.")

    if setup_finished or (WORLD_DIR / "region").exists():
        if TEMPLATE_DIR.exists():
            shutil.rmtree(TEMPLATE_DIR)
        print(f"[benchmark] Saving permanent extreme template to {TEMPLATE_DIR}...", flush=True)
        shutil.copytree(WORLD_DIR, TEMPLATE_DIR)
        print("[benchmark] Permanent Extreme World template successfully created!", flush=True)
    else:
        print("[benchmark] Failed to create permanent extreme world template.", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    generate()
