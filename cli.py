"""
cli.py
Command-line interface for the Automated File Organizer.

Usage:
    python cli.py organize <directory> [--dry-run] [--no-duplicates]
    python cli.py undo
    python cli.py history
    python cli.py serve [--port 8000]
"""

import sys
import argparse
import json

from organizer import organize, undo_last_run, list_runs


def print_summary(result: dict):
    mode = "DRY RUN (no files moved)" if result["dry_run"] else "COMPLETED"
    print(f"\n{'=' * 50}")
    print(f"  File Organizer — {mode}")
    print(f"{'=' * 50}")
    print(f"Target directory : {result['target_dir']}")
    print(f"Files scanned    : {result['total_files_scanned']}")
    print(f"Files moved      : {result['total_moved']}")

    if result["summary_by_category"]:
        print("\nBreakdown by category:")
        for category, count in result["summary_by_category"].items():
            if count > 0:
                print(f"  {category:<15} {count}")

    if result["duplicates_skipped"]:
        print(f"\nDuplicates skipped: {len(result['duplicates_skipped'])}")
        for dup in result["duplicates_skipped"]:
            print(f"  {dup['file']}  (same as {dup['duplicate_of']})")

    if result["errors"]:
        print(f"\nErrors encountered: {len(result['errors'])}")
        for err in result["errors"]:
            print(f"  {err['file']}: {err['error']}")

    if not result["dry_run"] and result["total_moved"] > 0:
        print(f"\nLog saved to: {result.get('log_file')}")
        print("Run 'python cli.py undo' to reverse this action.")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Automated File Organizer — sorts files into category folders."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    organize_parser = subparsers.add_parser("organize", help="Organize a directory")
    organize_parser.add_argument("directory", help="Path to the directory to organize")
    organize_parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without moving files"
    )
    organize_parser.add_argument(
        "--no-duplicates", action="store_true", help="Disable duplicate file detection"
    )

    subparsers.add_parser("undo", help="Undo the most recent organize run")
    subparsers.add_parser("history", help="Show history of past runs")

    serve_parser = subparsers.add_parser("serve", help="Launch the web dashboard")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to serve on")

    args = parser.parse_args()

    if args.command == "organize":
        try:
            result = organize(
                args.directory,
                dry_run=args.dry_run,
                detect_duplicates=not args.no_duplicates,
            )
            print_summary(result)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.command == "undo":
        try:
            result = undo_last_run()
            print(f"\nRestored {result['restored_count']} file(s).")
            if result["failed_count"]:
                print(f"Failed to restore {result['failed_count']} file(s):")
                for f in result["failed"]:
                    print(f"  {f}")
            print()
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.command == "history":
        runs = list_runs()
        if not runs:
            print("No runs found yet.")
        else:
            print(f"\n{'Timestamp':<22}{'Directory':<35}{'Moved':<8}{'Type'}")
            print("-" * 80)
            for run in runs:
                run_type = "dry-run" if run["dry_run"] else "live"
                print(
                    f"{run['timestamp'][:19]:<22}"
                    f"{run['target_dir'][:33]:<35}"
                    f"{run['total_moved']:<8}{run_type}"
                )
            print()

    elif args.command == "serve":
        from web.server import run_server
        run_server(port=args.port)


if __name__ == "__main__":
    main()
