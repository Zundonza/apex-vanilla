from pathlib import Path

content = Path("D:/apex-vanilla/benchmark/reports/torture-baseline-vanilla-26.3-flamegraph.html").read_text(encoding="utf-8")
idx1 = content.find("const cpool = [")
idx2 = content.find("];", idx1)
lines = [l.strip().strip("',") for l in content[idx1:idx2].splitlines()[1:] if l.strip()]

print(f"Total frames: {len(lines)}")
for l in lines:
    if any(k in l for k in ["tick", "Block", "Entity", "Hopper", "Villager", "Level", "Server", "Voxel"]):
        print("  ", l)
