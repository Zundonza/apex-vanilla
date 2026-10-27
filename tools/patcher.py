"""
Apex-Vanilla Toolchain Patcher
Handles Mojang latest server download, decompilation, patch application, and rebuilds.
"""

import sys
import os
import io
import glob
import json
import shutil
import hashlib
import urllib.request
import zipfile
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT_DIR / "cache"
WORK_DIR = ROOT_DIR / "work"
PATCHES_DIR = ROOT_DIR / "patches"
RUN_DIR = ROOT_DIR / "run"

VINEFLOWER_VERSION = "1.12.0"
VINEFLOWER_URL = f"https://github.com/Vineflower/vineflower/releases/download/{VINEFLOWER_VERSION}/vineflower-{VINEFLOWER_VERSION}.jar"

def log(msg: str):
    print(f"[apex-patcher] {msg}", flush=True)

def download_file(url: str, dest: Path):
    if dest.exists() and dest.stat().st_size > 0:
        log(f"Cached: {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f"Downloading: {url} -> {dest.name}...")
    urllib.request.urlretrieve(url, dest)
    log(f"Downloaded: {dest.name} ({dest.stat().st_size} bytes)")

def get_latest_release_version() -> str:
    manifest_path = CACHE_DIR / "version_manifest_v2.json"
    download_file("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json", manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    latest = manifest.get("latest", {}).get("release", "26.3")
    return latest

def get_version_info(target_version: str):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = CACHE_DIR / "version_manifest_v2.json"
    download_file("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json", manifest_path)
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    for v in manifest.get("versions", []):
        if v["id"] == target_version:
            v_url = v["url"]
            v_path = CACHE_DIR / f"{target_version}.json"
            download_file(v_url, v_path)
            with open(v_path, "r", encoding="utf-8") as vf:
                return json.load(vf)
    raise ValueError(f"Version {target_version} not found in Mojang manifest.")

def ensure_vineflower() -> Path:
    vf_jar = CACHE_DIR / f"vineflower-{VINEFLOWER_VERSION}.jar"
    download_file(VINEFLOWER_URL, vf_jar)
    return vf_jar

def setup(target_version: str = "latest"):
    if target_version == "latest":
        target_version = get_latest_release_version()
        
    log(f"Setting up vanilla environment for latest release: Minecraft {target_version}...")
    v_data = get_version_info(target_version)
    
    server_url = v_data["downloads"]["server"]["url"]
    server_jar = CACHE_DIR / f"server-{target_version}.jar"
    download_file(server_url, server_jar)
    
    mappings_info = v_data["downloads"].get("server_mappings")
    if mappings_info:
        mappings_file = CACHE_DIR / f"server_mappings-{target_version}.txt"
        download_file(mappings_info["url"], mappings_file)
        
    vf_jar = ensure_vineflower()
    
    bundled_dir = CACHE_DIR / f"bundled-{target_version}"
    if not bundled_dir.exists():
        log(f"Extracting bundler jar: {server_jar}...")
        bundled_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(server_jar, "r") as z:
            z.extractall(bundled_dir)
            
    internal_jar = None
    versions_dir = bundled_dir / "META-INF" / "versions"
    if versions_dir.exists():
        for candidate in versions_dir.rglob("*.jar"):
            internal_jar = candidate
            break
            
    if not internal_jar or not internal_jar.exists():
        internal_jar = server_jar
        
    log(f"Internal server jar: {internal_jar}")
    
    mc_work = WORK_DIR / "Minecraft"
    src_dir = mc_work / "src" / "net" / "minecraft"
    
    if not src_dir.exists():
        log(f"Decompiling {internal_jar.name} with Vineflower into {mc_work / 'src'}...")
        mc_work.mkdir(parents=True, exist_ok=True)
        (mc_work / "src").mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "java", "-jar", str(vf_jar),
            "--folder",
            "--log-level=warn",
            str(internal_jar),
            str(mc_work / "src")
        ]
        log(f"Running Vineflower decompiler...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            log(f"Decompiler warning/error: {res.stderr[:500]}")
            
        log("Initializing git repository in work/Minecraft...")
        subprocess.run(["git", "init"], cwd=mc_work, check=True)
        subprocess.run(["git", "checkout", "-b", "base"], cwd=mc_work, check=True)
        subprocess.run(["git", "add", "."], cwd=mc_work, check=True)
        subprocess.run(["git", "commit", "-m", f"Initial vanilla {target_version} import"], cwd=mc_work, check=True)
        subprocess.run(["git", "checkout", "-b", "core"], cwd=mc_work, check=True)
        log("work/Minecraft git tracking initialized.")
    else:
        log("Sources already decompiled in work/Minecraft.")

def apply_patches():
    mc_work = WORK_DIR / "Minecraft"
    if not mc_work.exists():
        log("work/Minecraft does not exist! Run setup first.")
        sys.exit(1)
        
    patches = sorted(PATCHES_DIR.glob("*.patch"))
    if not patches:
        log("No patches found in patches/ directory.")
        return
        
    log(f"Resetting work/Minecraft to base...")
    subprocess.run(["git", "checkout", "core"], cwd=mc_work, check=True)
    subprocess.run(["git", "reset", "--hard", "base"], cwd=mc_work, check=True)
    
    log(f"Applying {len(patches)} patches...")
    for patch in patches:
        log(f"  Applying {patch.name}...")
        res = subprocess.run(["git", "apply", "--3way", str(patch)], cwd=mc_work, capture_output=True, text=True)
        if res.returncode != 0:
            log(f"Error applying patch {patch.name}: {res.stderr}")
            sys.exit(1)
        subprocess.run(["git", "add", "."], cwd=mc_work, check=True)
        subprocess.run(["git", "commit", "-m", f"Patch: {patch.stem}"], cwd=mc_work, check=True)
    log("All patches applied successfully.")

def rebuild_patches():
    mc_work = WORK_DIR / "Minecraft"
    if not mc_work.exists():
        log("work/Minecraft does not exist!")
        sys.exit(1)
        
    PATCHES_DIR.mkdir(parents=True, exist_ok=True)
    for old_patch in PATCHES_DIR.glob("*.patch"):
        old_patch.unlink()
        
    log("Generating patch series from base..core...")
    res = subprocess.run(["git", "format-patch", "base..core", "-o", str(PATCHES_DIR)], cwd=mc_work, capture_output=True, text=True)
    if res.returncode != 0:
        log(f"Error generating patches: {res.stderr}")
        sys.exit(1)
        
    patches = list(PATCHES_DIR.glob("*.patch"))
    log(f"Generated {len(patches)} patches in patches/.")

def compile_modified_sources(mc_work: Path, version: str) -> Path:
    bin_dir = mc_work / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    libs = glob.glob(str(CACHE_DIR / f"bundled-{version}" / "META-INF" / "libraries" / "**" / "*.jar"), recursive=True)
    internal_jar = CACHE_DIR / f"bundled-{version}" / "META-INF" / "versions" / version / f"server-{version}.jar"
    cp = ";".join(libs) + ";" + str(internal_jar)

    # Find modified and untracked .java files
    status_res = subprocess.run(["git", "status", "--porcelain"], cwd=mc_work, capture_output=True, text=True, check=True)
    files_to_compile = []
    for line in status_res.stdout.splitlines():
        if line.strip():
            filepath = line[3:].strip()
            if filepath.endswith(".java") and (mc_work / filepath).exists():
                files_to_compile.append(str(mc_work / filepath))

    if not files_to_compile:
        # Check if diff between base and core has files
        diff_res = subprocess.run(["git", "diff", "--name-only", "base...core"], cwd=mc_work, capture_output=True, text=True)
        for filepath in diff_res.stdout.splitlines():
            if filepath.strip().endswith(".java") and (mc_work / filepath).exists():
                files_to_compile.append(str(mc_work / filepath))

    files_to_compile = sorted(list(set(files_to_compile)))
    if not files_to_compile:
        log("No modified Java files detected.")
        return bin_dir

    log(f"Compiling {len(files_to_compile)} modified Java files...")
    for f in files_to_compile:
        log(f"  Compiling: {Path(f).name}")

    javac_bin = r"D:\jdks\jdk-28\bin\javac.exe"
    cmd = [javac_bin, "-cp", cp, "-d", str(bin_dir)] + files_to_compile
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        log(f"Compilation error:\n{res.stderr}")
        sys.exit(1)

    log("Compilation completed successfully.")
    return bin_dir

def build_jar(target_version: str = "latest"):
    if target_version == "latest":
        target_version = get_latest_release_version()
        
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    mc_work = WORK_DIR / "Minecraft"
    dest_jar = RUN_DIR / "server.jar"
    base_bundler_jar = CACHE_DIR / f"server-{target_version}.jar"

    if not base_bundler_jar.exists():
        v_data = get_version_info(target_version)
        download_file(v_data["downloads"]["server"]["url"], base_bundler_jar)

    bin_dir = compile_modified_sources(mc_work, target_version)
    compiled_classes = list(bin_dir.rglob("*.class"))

    if not compiled_classes:
        log("No custom classes found. Copying vanilla bundler jar.")
        shutil.copyfile(base_bundler_jar, dest_jar)
        return

    log(f"Injecting {len(compiled_classes)} patched class files into server.jar...")
    temp_bundler = CACHE_DIR / "temp_server.jar"
    temp_inner_jar = CACHE_DIR / f"temp_server_{target_version}.jar"
    internal_jar_name = f"META-INF/versions/{target_version}/server-{target_version}.jar"

    # Step 1: Build the patched internal server jar
    with zipfile.ZipFile(base_bundler_jar, "r") as src_zip:
        inner_bytes = src_zip.read(internal_jar_name)

    clean_manifest = b"Manifest-Version: 1.0\r\nMain-Class: net.minecraft.server.Main\r\n\r\n"

    with zipfile.ZipFile(io.BytesIO(inner_bytes), "r") as src_inner:
        with zipfile.ZipFile(temp_inner_jar, "w", compression=zipfile.ZIP_STORED) as dst_inner:
            for inner_item in src_inner.infolist():
                name = inner_item.filename
                # Strip Mojang signatures and hash digests so JVM JarVerifier does not throw SecurityException
                if name == "META-INF/MANIFEST.MF":
                    dst_inner.writestr(name, clean_manifest)
                    continue
                if name.startswith("META-INF/") and (name.endswith(".SF") or name.endswith(".RSA") or name.endswith(".DSA")):
                    continue

                class_rel = name
                compiled_match = bin_dir / class_rel
                if not compiled_match.exists():
                    dst_inner.writestr(inner_item, src_inner.read(name))

            for c in compiled_classes:
                rel_path = str(c.relative_to(bin_dir)).replace("\\", "/")
                dst_inner.write(c, arcname=rel_path)

    # Compute sha256 of patched inner jar
    with open(temp_inner_jar, "rb") as f:
        inner_content = f.read()
        inner_sha256 = hashlib.sha256(inner_content).hexdigest()

    new_versions_list = f"{inner_sha256}\t{target_version}\t{target_version}/server-{target_version}.jar\n"

    # Step 2: Inject into bundler jar
    with zipfile.ZipFile(base_bundler_jar, "r") as src_zip:
        with zipfile.ZipFile(temp_bundler, "w", compression=zipfile.ZIP_DEFLATED) as dst_zip:
            for item in src_zip.infolist():
                if item.filename == internal_jar_name:
                    dst_zip.writestr(item.filename, inner_content)
                elif item.filename == "META-INF/versions.list":
                    dst_zip.writestr(item.filename, new_versions_list.encode("utf-8"))
                else:
                    dst_zip.writestr(item, src_zip.read(item.filename))

    shutil.move(temp_bundler, dest_jar)

    # Step 3: Also update run/versions/ direct cache if present
    run_version_dir = RUN_DIR / "versions" / target_version
    run_version_dir.mkdir(parents=True, exist_ok=True)
    target_cached_jar = run_version_dir / f"server-{target_version}.jar"
    shutil.copyfile(temp_inner_jar, target_cached_jar)
    if temp_inner_jar.exists():
        temp_inner_jar.unlink()

    log(f"Built patched server jar successfully: {dest_jar} ({dest_jar.stat().st_size} bytes)")
    log(f"Updated extracted runtime jar: {target_cached_jar}")

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "setup"
    version = sys.argv[2] if len(sys.argv) > 2 else "latest"
    
    if action == "setup":
        setup(version)
    elif action == "apply-patches":
        apply_patches()
    elif action == "rebuild-patches":
        rebuild_patches()
    elif action == "build-jar":
        build_jar(version)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
