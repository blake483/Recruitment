"""Bulk-import a folder of CVs (including sub-folders).

    python import_cvs.py "/path/to/CVs"          import everything in the folder
    python import_cvs.py --reparse               re-tag all stored CVs after editing taxonomy.py
"""

import argparse
import os
import sys

from cvsearch.db import Store
from cvsearch.extract import SUPPORTED_EXTENSIONS


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="*", help="folder(s) of CVs to import")
    ap.add_argument("--reparse", action="store_true", help="re-analyse every CV already in the database")
    ap.add_argument("--data", default=os.environ.get("CVSEARCH_DATA", "data"), help="data folder (default ./data)")
    args = ap.parse_args()
    if not args.folders and not args.reparse:
        ap.print_help()
        return 1

    store = Store(args.data)
    if args.reparse:
        print(f"Re-analysed {store.reparse_all()} CVs.")

    files = []
    for folder in args.folders:
        for root, _, names in os.walk(folder):
            for name in names:
                if os.path.splitext(name)[1].lower() in SUPPORTED_EXTENSIONS and not name.startswith(("~$", ".")):
                    files.append(os.path.join(root, name))

    counts = {"added": 0, "duplicate": 0, "unsupported": 0, "error": 0}
    problems = []
    for i, path in enumerate(files, 1):
        status, cid, message = store.add_file(path)
        counts[status] += 1
        if status == "error" or (status == "added" and message != "ok"):
            problems.append(f"  {path}: {message}")
        print(f"\r[{i}/{len(files)}] {counts['added']} added, {counts['duplicate']} duplicates", end="", flush=True)
    if files:
        print()
        print(f"Done. {counts['added']} added, {counts['duplicate']} already present, {len(problems)} need a look.")
    if problems:
        print("Files with problems (still searchable where text was found):")
        print("\n".join(problems))
    return 0


if __name__ == "__main__":
    sys.exit(main())
