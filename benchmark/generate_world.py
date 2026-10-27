"""
Benchmark Torture Chamber World Generator
Creates a deterministic Minecraft world with 4 heavy-load sectors:
- Sector 1: 250 Villagers with Beds and Lecterns (Brain & POI load)
- Sector 2: 1200 Interconnected Hoppers (Inventory & Entity Search load)
- Sector 3: Observer Clocks & Redstone Wire Cascades (Block update & Light load)
- Sector 4: 180 Stacked Cows in 2x2 Pen (Entity push & VoxelShape collision load)
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

def create_datapack():
    dp_dir = WORLD_DIR / "datapacks" / "torture"
    functions_dir = dp_dir / "data" / "benchmark" / "function"
    tags_dir = dp_dir / "data" / "minecraft" / "tags" / "function"
    functions_dir.mkdir(parents=True, exist_ok=True)
    tags_dir.mkdir(parents=True, exist_ok=True)

    # pack.mcmeta (pack_format for 26.x / 1.21.x)
    mcmeta = {
        "pack": {
            "pack_format": 61,
            "description": "Benchmark Torture Chamber Generator"
        }
    }
    with open(dp_dir / "pack.mcmeta", "w", encoding="utf-8") as f:
        json_str = str(mcmeta).replace("'", '"')
        f.write(json_str)

    # load.json tag
    load_tag = {
        "values": [
            "benchmark:build"
        ]
    }
    with open(tags_dir / "load.json", "w", encoding="utf-8") as f:
        f.write(str(load_tag).replace("'", '"'))

    # build.mcfunction
    lines = [
        "# Benchmark Initial Setup",
        "gamerule advance_time false",
        "gamerule advance_weather false",
        "gamerule spawn_mobs false",
        "gamerule spawn_monsters false",
        "gamerule random_tick_speed 0",
        "time set noon",
        "forceload add -4 -4 8 8",
        ""
    ]

    # Sector 1: 256 Villager POI Cells (16x16 grid)
    lines.append("# --- Sector 1: Villager & POI Grid (256 cells) ---")
    count = 0
    for x in range(16):
        for z in range(16):
            rx = x * 2
            rz = z * 2
            lines.append(f"setblock {rx} 60 {rz} minecraft:white_bed")
            lines.append(f"setblock {rx} 60 {rz+1} minecraft:lectern")
            lines.append(f"setblock {rx+1} 60 {rz} minecraft:smooth_stone")
            lines.append(f"setblock {rx} 61 {rz} minecraft:barrier")
            lines.append(f"summon minecraft:villager {rx}.5 60.5 {rz}.5 {{PersistenceRequired:1b,NoAI:0b}}")
            count += 1
    lines.append(f"# Placed {count} villagers with beds and lecterns.")
    lines.append("")

    # Sector 2: 1200 Hoppers
    lines.append("# --- Sector 2: Hopper Matrix (1200 hoppers) ---")
    lines.append("fill 40 60 0 59 60 29 minecraft:hopper[facing=east]")
    lines.append("fill 40 61 0 59 61 29 minecraft:hopper[facing=south]")
    lines.append("")

    # Sector 3: Redstone & Observer Clocks & Light Cascades
    lines.append("# --- Sector 3: Industrial Redstone ---")
    for r in range(10):
        rz = r * 3
        # Observer clock facing each other
        lines.append(f"setblock 70 60 {rz} minecraft:observer[facing=west]")
        lines.append(f"setblock 69 60 {rz} minecraft:observer[facing=east]")
        # Redstone dust cascade line
        lines.append(f"fill 71 60 {rz} 85 60 {rz} minecraft:redstone_wire")
        lines.append(f"fill 86 60 {rz} 90 60 {rz} minecraft:redstone_lamp")
    lines.append("")

    # Sector 4: 180 Packed Cows in 2x2 water pen
    lines.append("# --- Sector 4: Animal Collision Pen ---")
    lines.append("fill -21 60 -1 -18 63 2 minecraft:glass hollow")
    lines.append("setblock -20 60 0 minecraft:water")
    for _ in range(180):
        lines.append("summon minecraft:cow -19.5 60.5 0.5 {PersistenceRequired:1b}")

    lines.append("")
    lines.append('say [BENCHMARK_SETUP_COMPLETE]')

    with open(functions_dir / "build.mcfunction", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[benchmark] Datapack generated at {dp_dir}")

def get_java_exe() -> str:
    candidates = [
        Path(r"D:\jdks\jdk-28\bin\java.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "java"

def generate():
    if not (RUN_DIR / "server.jar").exists():
        print(f"[benchmark] Error: {RUN_DIR / 'server.jar'} does not exist. Run build-jar first.")
        sys.exit(1)

    print("[benchmark] Preparing run environment...")
    if WORLD_DIR.exists():
        shutil.rmtree(WORLD_DIR)
    WORLD_DIR.mkdir(parents=True, exist_ok=True)

    create_datapack()

    java_bin = get_java_exe()
    print(f"[benchmark] Starting server using {java_bin} in headless mode to generate and save world...")
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
        print(f"  [server] {line.strip()}")
        if "[BENCHMARK_SETUP_COMPLETE]" in line:
            setup_finished = True
            print("[benchmark] World generation and entities spawned! Stopping server...")
            proc.stdin.write("stop\n")
            proc.stdin.flush()
            break
        if time.time() - start_time > 180:
            print("[benchmark] Timeout waiting for world generation!")
            proc.kill()
            break

    proc.wait()
    print("[benchmark] Server stopped.")

    if setup_finished or (WORLD_DIR / "region").exists():
        if TEMPLATE_DIR.exists():
            shutil.rmtree(TEMPLATE_DIR)
        print(f"[benchmark] Saving template to {TEMPLATE_DIR}...")
        shutil.copytree(WORLD_DIR, TEMPLATE_DIR)
        print("[benchmark] World template successfully created!")
    else:
        print("[benchmark] Failed to create world template.")
        sys.exit(1)

if __name__ == "__main__":
    generate()
