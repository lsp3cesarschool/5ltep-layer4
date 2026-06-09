"""
Snapshot Compression — 5L-TEP Layer 4 Toolkit
==============================================
Compresses snapshot files older than RETENTION_DAYS in-place (gzip) and
updates data/snapshots/manifest.json to point at the new .gz filenames.

Combines with the content-addressed deduplication in main.py to keep
long-term repository storage bounded: identical observations are stored
once (dedup), and old unique snapshots are compressed (~85% reduction).

Safe to run repeatedly — already-compressed files are skipped, and the
manifest is only rewritten if at least one file was compressed.

Designed to be invoked from .github/workflows/compress.yml on a weekly
schedule, but can also be executed locally for testing.
"""

import gzip
import json
import logging
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("5ltep.compress")

SNAPSHOTS_DIR = Path("data/snapshots")
MANIFEST_FILE = SNAPSHOTS_DIR / "manifest.json"
RETENTION_DAYS = 90

SNAPSHOT_PATTERN = re.compile(r"^snapshot_(\d{8}T\d{6}Z)\.json$")


def parse_run_id(run_id: str) -> datetime:
    """Parse the run_id timestamp embedded in snapshot filenames."""
    return datetime.strptime(run_id, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def compress_file(src: Path) -> Path:
    """Gzip a file in place at maximum compression and remove the original."""
    dst = src.with_suffix(src.suffix + ".gz")
    with open(src, "rb") as fi, gzip.open(dst, "wb", compresslevel=9) as fo:
        shutil.copyfileobj(fi, fo)
    src.unlink()
    return dst


def main() -> int:
    if not MANIFEST_FILE.exists():
        logger.info("No manifest found at %s — nothing to compress.", MANIFEST_FILE)
        return 0

    with open(MANIFEST_FILE, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    threshold = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    logger.info(
        "Compression threshold: %s (snapshots older than %d days)",
        threshold.isoformat(), RETENTION_DAYS,
    )

    compressed = 0
    skipped = 0
    saved_bytes = 0

    for snap_hash, fname in list(manifest["snapshots"].items()):
        if fname.endswith(".gz"):
            skipped += 1
            continue

        match = SNAPSHOT_PATTERN.match(fname)
        if not match:
            logger.warning("Skipping unrecognized filename: %s", fname)
            skipped += 1
            continue

        ts = parse_run_id(match.group(1))
        if ts >= threshold:
            skipped += 1
            continue

        src = SNAPSHOTS_DIR / fname
        if not src.exists():
            logger.warning("Manifest references missing file: %s", fname)
            skipped += 1
            continue

        before = src.stat().st_size
        dst = compress_file(src)
        after = dst.stat().st_size
        saved_bytes += (before - after)

        manifest["snapshots"][snap_hash] = dst.name
        compressed += 1
        ratio = (1 - after / before) * 100 if before else 0
        logger.info(
            "Compressed %s (%d KB -> %d KB, %.0f%% reduction)",
            fname, before // 1024, after // 1024, ratio,
        )

    if compressed:
        with open(MANIFEST_FILE, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
        logger.info(
            "Done — compressed %d snapshots, saved %.2f MB total.",
            compressed, saved_bytes / 1024 / 1024,
        )
    else:
        logger.info(
            "Nothing to compress (skipped %d entries: already-gzipped or within retention window).",
            skipped,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
