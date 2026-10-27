"""
Download profiler utilities: jfr-converter for interactive HTML Flamegraphs from JFR records.
"""

import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools" / "profiler"
TOOLS_DIR.mkdir(parents=True, exist_ok=True)

JFR_CONVERTER_URL = "https://github.com/async-profiler/async-profiler/releases/download/v4.6/jfr-converter.jar"
DEST_JAR = TOOLS_DIR / "jfr-converter.jar"

def setup_profiler():
    if DEST_JAR.exists() and DEST_JAR.stat().st_size > 0:
        print(f"[profiler] jfr-converter.jar already cached at {DEST_JAR}")
        return DEST_JAR
    print(f"[profiler] Downloading jfr-converter.jar from {JFR_CONVERTER_URL}...")
    urllib.request.urlretrieve(JFR_CONVERTER_URL, DEST_JAR)
    print(f"[profiler] Downloaded: {DEST_JAR} ({DEST_JAR.stat().st_size} bytes)")
    return DEST_JAR

if __name__ == "__main__":
    setup_profiler()
