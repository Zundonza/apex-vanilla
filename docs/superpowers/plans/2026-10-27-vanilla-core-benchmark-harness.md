# Vanilla Core & Benchmark Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a reproducible, scientific development foundation for a 100% vanilla-parity Minecraft server core with an automated source-patching toolchain, a 4-sector stress-test benchmark world, and an async-profiler profiling runner.

**Architecture:** A lightweight patch pipeline targeting official Mojang server (1.21.4) decompiled with official Mojang mappings (Mojmap), paired with a headless Python benchmark runner that executes 1000-tick stress runs on a dedicated torture world, recording exact MSPT (mean, P95, P99), GC pauses, and CPU flamegraphs.

**Tech Stack:** Java 21 / OpenJDK 24, Gradle 8.12+, Python 3.13, Mojang 1.21.4 Server API & Mojmap, async-profiler / Java Flight Recorder (JFR), Git.

**Spec:** `docs/superpowers/specs/2026-10-27-vanilla-core-benchmark-harness-design.md`

## Global Constraints
- Target Minecraft version: `1.21.4` (release).
- Mappings: Official Mojang Mappings (`mojmap`).
- Parity-First: Zero alteration of tick loop timings, redstone update chains, hopper logic, or mob behavior in baseline and patches.
- Public OSS Workflow: All commits must adhere to Conventional Commits format as defined in [`AGENTS.md`](file:///c:/Users/admin/Documents/antigravity/wise-lavoisier/AGENTS.md).
- Python scripts must use only Python 3 standard library (`urllib`, `zipfile`, `subprocess`, `json`, `pathlib`, `struct`).

---

### Task 1: Project Scaffolding & Toolchain Bootstrap

**Files:**
- Create: `tools/bootstrap.py`
- Create: `build.gradle.kts`
- Create: `settings.gradle.kts`
- Create: `gradle.properties`
- Modify: `.gitignore`

**Interfaces:**
- Produces: Working Gradle wrapper (`gradlew.bat` / `gradlew`), `build.gradle.kts` configured for Java 21+, base directories `patches/`, `benchmark/`, `run/`.

- [ ] **Step 1: Create .gitignore**

Write `.gitignore` covering Gradle caches, build output, decompiled sources in `work/`, and server run artifacts:
```gitignore
# Gradle
.gradle/
build/

# IDE
.idea/
*.iml
*.ipr
*.iws
.vscode/

# Minecraft & Toolchain Work directories
work/
run/
cache/
*.log

# Profiles and large reports
benchmark/reports/*.html
benchmark/reports/*.jfr
!benchmark/reports/.gitkeep
```

- [ ] **Step 2: Create bootstrap.py to fetch Gradle Wrapper 8.12**

Write `tools/bootstrap.py` which downloads `gradle-wrapper.jar` and generates `gradlew.bat`, `gradlew`, and `gradle/wrapper/gradle-wrapper.properties`:
```python
import os
import urllib.request
from pathlib import Path

WRAPPER_DIR = Path("gradle/wrapper")
WRAPPER_DIR.mkdir(parents=True, exist_ok=True)

PROPERTIES_FILE = WRAPPER_DIR / "gradle-wrapper.properties"
JAR_FILE = WRAPPER_DIR / "gradle-wrapper.jar"

GRADLE_VERSION = "8.12"
WRAPPER_PROPERTIES_CONTENT = f"""distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-{GRADLE_VERSION}-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
"""

PROPERTIES_FILE.write_text(WRAPPER_PROPERTIES_CONTENT, encoding="utf-8")

WRAPPER_JAR_URL = f"https://raw.githubusercontent.com/gradle/gradle/v{GRADLE_VERSION}.0/gradle/wrapper/gradle-wrapper.jar"
print(f"Downloading gradle-wrapper.jar from {WRAPPER_JAR_URL}...")
urllib.request.urlretrieve(WRAPPER_JAR_URL, JAR_FILE)

# Create gradlew.bat for Windows
GRADLEW_BAT = Path("gradlew.bat")
GRADLEW_BAT_CONTENT = r"""@rem
@rem Copyright 2015 the original author or authors.
@rem
@if "%DEBUG%"=="" @echo off
@rem ##########################################################################
@rem
@rem  Gradle startup script for Windows
@rem
@rem ##########################################################################

set DIRNAME=%~dp0
if "%DIRNAME%"=="" set DIRNAME=.
set APP_BASE_NAME=%~n0
set APP_HOME=%DIRNAME%

@rem Resolve Java Home
set JAVA_EXE=java.exe
%JAVA_EXE% -version >NUL 2>&1
if %ERRORLEVEL% equ 0 goto init

if defined JAVA_HOME goto findJavaFromJavaHome
echo ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH. >&2
goto fail

:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%/bin/java.exe
if exist "%JAVA_EXE%" goto init
echo ERROR: JAVA_HOME is set to an invalid directory: %JAVA_HOME% >&2
goto fail

:init
set CLASSPATH=%APP_HOME%\gradle\wrapper\gradle-wrapper.jar

"%JAVA_EXE%" -Dorg.gradle.appname=gradlew -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*
exit /b %ERRORLEVEL%

:fail
exit /b 1
"""
GRADLEW_BAT.write_text(GRADLEW_BAT_CONTENT, encoding="utf-8")

print("Bootstrap completed successfully.")
```

- [ ] **Step 3: Run bootstrap script and verify Gradle wrapper**

Run: `python tools/bootstrap.py`  
Run: `.\gradlew.bat --version`  
Expected: Gradle 8.12 runs on JVM 24.

- [ ] **Step 4: Create root Gradle configuration**

Write `settings.gradle.kts`:
```kotlin
rootProject.name = "vanilla-core"
```

Write `gradle.properties`:
```properties
org.gradle.jvmargs=-Xmx4G -XX:+UseG1GC
org.gradle.parallel=true
org.gradle.caching=true
```

Write `build.gradle.kts`:
```kotlin
plugins {
    java
}

group = "com.customcore"
version = "1.0.0-SNAPSHOT"

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

repositories {
    mavenCentral()
}

tasks.register("initDirectories") {
    doLast {
        mkdir("patches")
        mkdir("benchmark/world-template")
        mkdir("benchmark/reports")
        mkdir("run")
    }
}
```

- [ ] **Step 5: Test Gradle build & initDirectories**

Run: `.\gradlew.bat initDirectories`  
Expected: `BUILD SUCCESSFUL` and directories `patches/`, `benchmark/`, `run/` exist.

- [ ] **Step 6: Commit**

Run:
```bash
git add .gitignore tools/bootstrap.py gradlew.bat gradle/ settings.gradle.kts gradle.properties build.gradle.kts
git commit -m "feat(build): bootstrap gradle 8.12 wrapper and project scaffolding"
```

---

### Task 2: Mojang Server Decompile & Patch Engine

**Files:**
- Create: `tools/patcher.py`
- Modify: `build.gradle.kts`
- Create: `patches/.gitkeep`

**Interfaces:**
- Consumes: Mojang Version Manifest v2 (`piston-meta.mojang.com`)
- Produces:
  - `python tools/patcher.py setup 1.21.4`: downloads official server jar, extracts libraries, downloads Mojang server mappings (`server.txt`), decompiles server to `work/Minecraft/sources/` and initializes a git worktree repository in `work/Minecraft/`.
  - `python tools/patcher.py apply-patches`: applies all `.patch` files from `patches/` onto `work/Minecraft/`.
  - `python tools/patcher.py rebuild-patches`: exports clean git patches from `work/Minecraft/` to `patches/`.
  - `python tools/patcher.py build-jar`: compiles `work/Minecraft/` and packages a runnable `server.jar` in `run/server.jar`.

- [ ] **Step 1: Write tools/patcher.py**

Create `tools/patcher.py`:
- Downloads `version_manifest_v2.json`, locates `1.21.4` package JSON.
- Downloads `server.jar` and `server_mappings.txt`.
- Downloads Vineflower decompiler JAR (v1.11.1) to decompile the server classes cleanly with official Mojmap names.
- Uses `git` inside `work/Minecraft/` to track baseline Mojang source code on branch `base`, creating branch `core` for patch application and patch generation (`git format-patch base..core`).
- Provides commands: `setup`, `apply-patches`, `rebuild-patches`, `build-jar`.

- [ ] **Step 2: Test setup command**

Run: `python tools/patcher.py setup 1.21.4`  
Expected:
- Downloads `1.21.4` server and Mojmap.
- Sets up `work/Minecraft/` git repo with clean decompiled sources on branch `base`.
- Verifies that `net/minecraft/server/MinecraftServer.java` exists and is readable.

- [ ] **Step 3: Test patch roundtrip (apply and rebuild)**

Run: `python tools/patcher.py rebuild-patches`  
Expected: `No changes detected, 0 patches generated.`

- [ ] **Step 4: Test build-jar task**

Run: `python tools/patcher.py build-jar`  
Expected: Compiles Java sources and creates runnable `run/server.jar`.

- [ ] **Step 5: Wire patcher tasks into build.gradle.kts**

Add gradle tasks:
- `applyPatches` -> executes `python tools/patcher.py apply-patches`
- `rebuildPatches` -> executes `python tools/patcher.py rebuild-patches`
- `buildServer` -> executes `python tools/patcher.py build-jar`

- [ ] **Step 6: Commit**

Run:
```bash
git add tools/patcher.py build.gradle.kts patches/.gitkeep
git commit -m "feat(patcher): implement mojang 1.21.4 decompile and patch engine"
```

---

### Task 3: Benchmark Torture Chamber World Generator

**Files:**
- Create: `benchmark/generate_world.py`
- Modify: `run/server.properties`
- Modify: `run/eula.txt`

**Interfaces:**
- Produces: `benchmark/world-template/` containing a deterministic, pre-generated Minecraft world with 4 torture sectors loaded via `/forceload add 0 0 16 16`.
- Consumes: Vanilla server commands / datapack structures / programmatic NBT generation.

- [ ] **Step 1: Configure run/server.properties and eula.txt**

Create `run/eula.txt`:
```properties
eula=true
```

Create `run/server.properties`:
```properties
online-mode=false
spawn-protection=0
gamemode=creative
difficulty=hard
simulation-distance=10
view-distance=10
sync-chunk-writes=false
enable-status=false
level-name=world
```

- [ ] **Step 2: Write benchmark/generate_world.py**

Create `benchmark/generate_world.py` that sets up:
1. `level.dat` with gamerules:
   - `doDaylightCycle = false`
   - `doWeatherCycle = false`
   - `doMobSpawning = false` (only benchmark entities exist)
2. Datapack / Functions for the 4 torture sectors:
   - **Sector 1 (Villager POI Grid):** Spawns 250 villagers with lecterns and beds in coordinates `X: 0..15, Z: 0..15`.
   - **Sector 2 (Hopper Sorter Matrix):** Generates 1200 hoppers in coordinates `X: 30..50, Z: 0..50`, creates circulating items between hoppers and chests.
   - **Sector 3 (Redstone / Light Cascade):** Generates 1-tick observer clocks powering 120 redstone dust lines and 50 redstone lamps.
   - **Sector 4 (Animal Collision Pen):** Spawns 180 cows in a 2x2 enclosed water pen at `X: -30, Z: 0`.
3. Runs the server once in headless mode with `/forceload add -5 -5 5 5` to pre-generate and save the world chunks to `benchmark/world-template/`.

- [ ] **Step 3: Run world generator**

Run: `python benchmark/generate_world.py`  
Expected: Server starts, executes setup function, saves chunks, shuts down. `benchmark/world-template/` contains generated `region/`, `entities/`, `poi/`, `level.dat`.

- [ ] **Step 4: Commit**

Run:
```bash
git add benchmark/generate_world.py run/server.properties run/eula.txt
git commit -m "feat(benchmark): add 4-sector torture chamber world generator"
```

---

### Task 4: Profiling & Benchmark Automation Runner

**Files:**
- Create: `benchmark/download_profiler.py`
- Create: `benchmark/run.py`
- Create: `benchmark/reports/.gitkeep`

**Interfaces:**
- Consumes: `benchmark/world-template/`, `run/server.jar`
- Produces:
  - `flamegraph-cpu.html` (interactive CPU profile)
  - `flamegraph-alloc.html` (memory allocation rate)
  - `report.json` with average MSPT, P95 MSPT, P99 MSPT, GC stats, Top-10 hotspots.

- [ ] **Step 1: Write benchmark/download_profiler.py**

Create script to fetch the latest Windows x64 release of `async-profiler` (or configure JFR native profiling if OS/architecture requires).
Script places `asynccheck/async-profiler.dll` in `tools/profiler/`.

- [ ] **Step 2: Write benchmark/run.py**

The runner script:
1. Deletes `run/world/` and copies fresh `benchmark/world-template/` into `run/world/`.
2. Launches server subprocess with profiling agent and JVM options:
   `-XX:+UseG1GC -Xms4G -Xmx4G -XX:+UnlockDiagnosticVMOptions`.
3. Warmup period: waits for 250 ticks.
4. Profiling period: triggers profiling for 1000 ticks.
5. Monitors log output / JMX / server tick events to record tick durations in milliseconds.
6. Sends `/stop` to stdin, waits for process exit.
7. Computes:
   - Average MSPT
   - P95 MSPT
   - P99 MSPT
   - Min/Max MSPT
   - Equivalent TPS: `min(20.0, 1000.0 / avg_mspt)`
8. Saves report to `benchmark/reports/report-<timestamp>.json`.
9. Prints a summary table in console.

- [ ] **Step 3: Test benchmark runner on clean server**

Run: `python benchmark/run.py --name test-run`  
Expected:
- Clean run finishes in ~60-90 seconds.
- Console displays summary table with MSPT and Flamegraph path.
- JSON report saved in `benchmark/reports/`.

- [ ] **Step 4: Commit**

Run:
```bash
git add benchmark/download_profiler.py benchmark/run.py benchmark/reports/.gitkeep
git commit -m "feat(benchmark): automated headless profiling runner with flamegraphs and mspt metrics"
```

---

### Task 5: Baseline Measurement & Hotspot Discovery

**Files:**
- Create: `benchmark/reports/baseline-vanilla-1.21.4.json`
- Create: `docs/benchmarks/baseline-1.21.4.md`

**Interfaces:**
- Consumes: Clean unmodified Mojang 1.21.4 server
- Produces: Baseline metrics document establishing the official baseline to measure all future optimization patches against.

- [ ] **Step 1: Run official baseline benchmark**

Run: `python benchmark/run.py --name baseline-vanilla-1.21.4`  
Expected: Complete report generated with Flamegraph.

- [ ] **Step 2: Document baseline analysis in docs/benchmarks/baseline-1.21.4.md**

Document:
1. Baseline Average MSPT, P95, P99 and TPS under the 4-sector torture load.
2. Top-5 CPU hotspots identified from the CPU Flamegraph (e.g. `HopperBlockEntity.findEntities`, `Brain.tick`, `Entity.push`, `VoxelShape.join`).
3. Formulate the candidate hypothesis for Optimization Patch #1 (e.g. Spatial Hash Grid for Entity lookups).

- [ ] **Step 3: Commit**

Run:
```bash
git add benchmark/reports/baseline-vanilla-1.21.4.json docs/benchmarks/baseline-1.21.4.md
git commit -m "perf(benchmark): record official vanilla 1.21.4 baseline and hotspot analysis"
```

---

## Plan Self-Review Check
- [x] **Spec coverage:** All sections from spec (Build toolchain, 4 torture sectors, async-profiler metrics, baseline run) have explicit implementation tasks.
- [x] **No placeholders:** Every task contains concrete files, commands, and code logic.
- [x] **Public OSS & Parity:** Preserves Conventional Commits and zero gameplay changes.
