"""
organizer.py
Core engine for the Automated File Organizer.

Responsibilities:
- Classify files into categories based on extension
- Move files into category folders (with collision-safe renaming)
- Log every action to a JSON log file (so moves can be undone)
- Provide an undo() function that reverses the last run

Pure Python standard library only — no third-party dependencies.
"""

import os
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration: extension -> category mapping
# ---------------------------------------------------------------------------

CATEGORY_MAP = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md"],
    "Spreadsheets": [".xls", ".xlsx", ".csv", ".ods"],
    "Presentations": [".ppt", ".pptx", ".odp"],
    "Videos": [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".json", ".xml", ".sh"],
    "Executables": [".exe", ".msi", ".apk", ".bat", ".sh"],
    "Fonts": [".ttf", ".otf", ".woff", ".woff2"],
}

OTHERS_FOLDER = "Others"
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_category(file_path: Path) -> str:
    """Return the category name for a given file based on its extension."""
    ext = file_path.suffix.lower()
    for category, extensions in CATEGORY_MAP.items():
        if ext in extensions:
            return category
    return OTHERS_FOLDER


def _unique_destination(dest_folder: Path, filename: str) -> Path:
    """
    Avoid overwriting files with the same name by appending a counter.
    e.g. report.pdf -> report (1).pdf -> report (2).pdf
    """
    dest = dest_folder / filename
    if not dest.exists():
        return dest

    stem = dest.stem
    suffix = dest.suffix
    counter = 1
    while True:
        candidate = dest_folder / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _file_hash(path: Path, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash of a file (used for duplicate detection)."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def organize(
    target_dir: str,
    dry_run: bool = False,
    detect_duplicates: bool = True,
) -> dict:
    """
    Organize all files in `target_dir` into category subfolders.

    Args:
        target_dir: directory to organize
        dry_run: if True, only simulate and report what WOULD happen
        detect_duplicates: if True, skip moving exact duplicate files
                            and report them separately

    Returns:
        A summary dict with stats and the list of actions taken
        (also written to a timestamped JSON log file for undo support).
    """
    target_path = Path(target_dir).expanduser().resolve()
    if not target_path.exists() or not target_path.is_dir():
        raise FileNotFoundError(f"Target directory does not exist: {target_path}")

    actions = []
    duplicates = []
    seen_hashes = {}
    summary = {category: 0 for category in CATEGORY_MAP}
    summary[OTHERS_FOLDER] = 0
    errors = []

    # Only look at files directly inside target_dir (not already-organized subfolders)
    files = [f for f in target_path.iterdir() if f.is_file()]

    for file_path in files:
        try:
            # Skip the organizer's own log/script files if run inside its own folder
            if file_path.name in ("organizer.py", "cli.py"):
                continue

            if detect_duplicates:
                file_hash = _file_hash(file_path)
                if file_hash in seen_hashes:
                    duplicates.append({
                        "file": str(file_path),
                        "duplicate_of": str(seen_hashes[file_hash]),
                    })
                    continue
                seen_hashes[file_hash] = file_path

            category = get_category(file_path)
            dest_folder = target_path / category
            dest_path = _unique_destination(dest_folder, file_path.name)

            action = {
                "source": str(file_path),
                "destination": str(dest_path),
                "category": category,
            }

            if not dry_run:
                dest_folder.mkdir(exist_ok=True)
                shutil.move(str(file_path), str(dest_path))

            actions.append(action)
            summary[category] += 1

        except (OSError, PermissionError) as e:
            errors.append({"file": str(file_path), "error": str(e)})

    result = {
        "target_dir": str(target_path),
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "total_files_scanned": len(files),
        "total_moved": len(actions),
        "summary_by_category": summary,
        "duplicates_skipped": duplicates,
        "errors": errors,
        "actions": actions,
    }

    if not dry_run:
        log_file = LOG_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        result["log_file"] = str(log_file)

    return result


def undo_last_run() -> dict:
    """
    Reverse the most recent organize() run by reading its log file
    and moving every file back to its original location.
    """
    log_files = sorted(LOG_DIR.glob("run_*.json"))
    if not log_files:
        raise FileNotFoundError("No previous run found to undo.")

    last_log = log_files[-1]
    with open(last_log, "r", encoding="utf-8") as f:
        run_data = json.load(f)

    restored = []
    failed = []

    for action in run_data["actions"]:
        src = Path(action["destination"])  # current location (after move)
        dest = Path(action["source"])      # original location (before move)
        try:
            if src.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
                restored.append(str(dest))
            else:
                failed.append(str(src))
        except (OSError, PermissionError) as e:
            failed.append(f"{src} ({e})")

    last_log.rename(last_log.with_suffix(".undone.json"))

    return {
        "restored_count": len(restored),
        "failed_count": len(failed),
        "restored": restored,
        "failed": failed,
    }


def list_runs() -> list:
    """Return metadata for all past organize runs (for dashboard history view)."""
    runs = []
    for log_file in sorted(LOG_DIR.glob("run_*.json"), reverse=True):
        with open(log_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        runs.append({
            "log_file": log_file.name,
            "timestamp": data.get("timestamp"),
            "target_dir": data.get("target_dir"),
            "total_moved": data.get("total_moved"),
            "dry_run": data.get("dry_run"),
        })
    return runs
