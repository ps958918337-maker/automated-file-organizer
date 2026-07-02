# Automated File Organizer

**Intern ID:** `[YOUR_INTERN_ID]`  
**Full Name:** `[YOUR_FULL_NAME]`  
**No. of Weeks:** `[NUMBER_OF_WEEKS]`  
**Project Name:** Automated File Organizer  
**Project Scope:** A Python-based utility that automatically sorts files in a given directory into categorized folders (Images, Documents, Videos, etc.) based on their extensions. It features both a command-line interface and a locally hosted web dashboard. Key functionalities include duplicate detection, safe renaming, dry-run previews, and full undo capabilities to ensure data safety.

---

A Python tool that automatically sorts messy directories (like Downloads)
into category folders — Images, Documents, Videos, Code, etc. — based on
file extension. Includes a CLI and a web dashboard, both built with the
Python **standard library only** (no Flask, FastAPI, or other third-party
frameworks).

## Features

- **Automatic classification** — 10 built-in categories (Images, Documents,
  Spreadsheets, Presentations, Videos, Audio, Archives, Code, Executables,
  Fonts) covering 50+ file extensions, with an `Others` catch-all.
- **Duplicate detection** — SHA-256 content hashing skips exact duplicate
  files instead of moving them.
- **Collision-safe renaming** — if a destination filename already exists,
  the tool appends `(1)`, `(2)`, etc. instead of overwriting.
- **Dry-run mode** — preview exactly what would happen before touching
  any files.
- **Undo support** — every run is logged to JSON; `undo` reverses the most
  recent run by moving files back to their original locations.
- **Run history** — past runs are tracked and viewable from both the CLI
  and the dashboard.
- **Web dashboard** — a single-page UI to trigger runs, see a live
  breakdown by category, and review history, served by a hand-rolled
  `http.server` backend (no external web framework).

## Project structure

```
file_organizer/
├── organizer.py        # Core engine: classification, move, undo, logging
├── cli.py               # Command-line interface
├── web/
│   ├── server.py         # Stdlib http.server backend + JSON API
│   └── static/
│       └── index.html    # Dashboard UI (HTML/CSS/JS, no framework)
└── logs/                 # Auto-created; one JSON file per run (for undo)
```

## Usage

### CLI

```bash
# Preview what would happen (no files are moved)
python cli.py organize /path/to/folder --dry-run

# Actually organize the folder
python cli.py organize /path/to/folder

# Organize without duplicate detection
python cli.py organize /path/to/folder --no-duplicates

# Undo the most recent run
python cli.py undo

# View history of past runs
python cli.py history
```

### Web dashboard

```bash
python cli.py serve --port 8000
```

Then open `http://localhost:8000` in a browser. Enter a directory path,
choose dry-run / duplicate-detection options, and click **Run organizer**.
The dashboard shows a live per-category breakdown, the full list of file
moves, and run history — with a one-click **Undo last run** button.

## How it works

1. `organize()` scans the top level of the target directory (it does not
   recurse into subfolders, so already-organized folders are left alone).
2. Each file's extension is matched against `CATEGORY_MAP` to decide its
   category; unmatched extensions go to `Others`.
3. If duplicate detection is on, each file is hashed (SHA-256); files with
   a hash already seen in this run are skipped and reported separately.
4. Files are moved into `<target_dir>/<Category>/`, creating the folder if
   needed. Name collisions are resolved by appending a counter.
5. Every move is recorded in a timestamped JSON log under `logs/`.
6. `undo_last_run()` reads the most recent log and moves every file back
   to its original path, then marks the log as `.undone.json` so it won't
   be undone twice.

## Design notes (for interview talking points)

- **Why stdlib only?** Demonstrates the tool works anywhere Python is
  installed, with zero `pip install` steps — useful for a lightweight
  utility that might run on shared or restricted machines. It also keeps
  the dependency surface (and attack surface) minimal.
- **Why JSON logs instead of a database?** The use case is simple
  (one log per run, read sequentially for undo/history) so a lightweight,
  human-readable, dependency-free format was a better fit than adding
  SQLite/ORM overhead for this scale.
- **Why hash-based duplicate detection instead of filename matching?**
  Filenames can differ while content is identical (or vice versa).
  Hashing the content is the only reliable way to detect true duplicates.
- **Why not recurse into subfolders?** Recursing could re-organize files
  that were already sorted in a previous run, or touch folders the user
  didn't intend to flatten. Scanning only the top level keeps the tool's
  behavior predictable and non-destructive by default.

## Screenshots and Output

*Replace these placeholders with actual images of your output:*

**Web Dashboard:**
![Web Dashboard Output](path/to/web_dashboard_screenshot.png)

**CLI Output:**
![CLI Output](path/to/cli_output_screenshot.png)
