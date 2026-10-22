#!/usr/bin/env python3
"""Sloth Sorter: a lazy, local file tidier powered by an open-weight model.

Reads each file in a messy folder, asks a local LLM (via Ollama) where it
belongs and what to call it, then files it away. Nothing leaves your machine.
Dry-run by default. Every move is undoable.
"""
import argparse
import json
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
UNDO_LOG = ".sloth-undo.json"

CATEGORIES = ["Documents", "Images", "Code", "Data", "Archives",
              "Installers", "Media", "Receipts", "Other"]

TEXT_EXT = {".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".log", ".yaml", ".yml"}

FALLBACK = {
    "Documents": {".pdf", ".doc", ".docx", ".odt", ".txt", ".md"},
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".heic"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".sh", ".ipynb"},
    "Data": {".csv", ".json", ".xlsx", ".parquet", ".sql"},
    "Archives": {".zip", ".tar", ".gz", ".7z", ".rar"},
    "Installers": {".dmg", ".exe", ".msi", ".pkg", ".deb", ".apk"},
    "Media": {".mp3", ".mp4", ".mov", ".wav", ".mkv", ".m4a"},
}

SYSTEM = (
    "You are a tidy, minimal file librarian. Given a file's name, type and a "
    "short preview, reply with JSON only: "
    '{"category": <one of ' + json.dumps(CATEGORIES) + '>, '
    '"name": <short descriptive kebab-case name, no extension>}. '
    "Prefer 'Receipts' for invoices and purchase confirmations."
)


def peek(path: Path, limit: int = 600) -> str:
    if path.suffix.lower() not in TEXT_EXT:
        return ""
    try:
        return path.read_text(errors="ignore")[:limit]
    except OSError:
        return ""


def fallback_category(path: Path) -> str:
    ext = path.suffix.lower()
    return next((c for c, exts in FALLBACK.items() if ext in exts), "Other")


def ask_model(model: str, path: Path) -> dict:
    user = f"File: {path.name}\nSize: {path.stat().st_size} bytes\nPreview:\n{peek(path)}"
    body = json.dumps({
        "model": model, "stream": False, "format": "json",
        "options": {"temperature": 0},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(json.loads(r.read())["message"]["content"])


def clean_name(raw: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(raw).lower()).strip("-")[:60]
    return slug or fallback


def unique(dest: Path) -> Path:
    n, cand = 1, dest
    while cand.exists():
        cand = dest.with_name(f"{dest.stem}-{n}{dest.suffix}")
        n += 1
    return cand


def plan(folder: Path, model: str, min_age: int, rename: bool):
    cutoff = time.time() - min_age * 60
    moves, offline = [], False
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.name.startswith(".") or f.stat().st_mtime > cutoff:
            continue
        category, stem = fallback_category(f), f.stem
        if not offline:
            try:
                ans = ask_model(model, f)
                if ans.get("category") in CATEGORIES:
                    category = ans["category"]
                if rename:
                    stem = clean_name(ans.get("name"), f.stem)
            except Exception as e:
                offline = True
                print(f"! Model unavailable ({e.__class__.__name__}); using file extensions.\n",
                      file=sys.stderr)
        dest = unique(folder / category / f"{stem}{f.suffix.lower()}")
        moves.append((f, dest))
    return moves


def apply(moves):
    done = []
    for src, dst in moves:
        dst.parent.mkdir(exist_ok=True)
        shutil.move(str(src), str(dst))
        done.append([str(dst), str(src)])
    return done


def undo(folder: Path):
    log = folder / UNDO_LOG
    if not log.exists():
        sys.exit("Nothing to undo.")
    for dst, src in reversed(json.loads(log.read_text())):
        if Path(dst).exists() and not Path(src).exists():
            shutil.move(dst, src)
            print(f"restored {Path(src).name}")
    log.unlink()


def main():
    p = argparse.ArgumentParser(description="Lazy local file tidier.")
    p.add_argument("folder", type=Path)
    p.add_argument("--model", default="llama3.2:3b", help="any Ollama model")
    p.add_argument("--apply", action="store_true", help="actually move files")
    p.add_argument("--undo", action="store_true", help="revert the last run")
    p.add_argument("--no-rename", action="store_true", help="only sort, keep names")
    p.add_argument("--min-age", type=int, default=10,
                   help="skip files modified in the last N minutes")
    a = p.parse_args()
    folder = a.folder.expanduser().resolve()

    if a.undo:
        return undo(folder)

    moves = plan(folder, a.model, a.min_age, not a.no_rename)
    if not moves:
        return print("Already tidy. Sloth approves.")
    for src, dst in moves:
        print(f"{src.name:40.40}  ->  {dst.relative_to(folder)}")
    if not a.apply:
        return print(f"\nDry run: {len(moves)} files. Re-run with --apply to do it.")
    (folder / UNDO_LOG).write_text(json.dumps(apply(moves)))
    print(f"\nMoved {len(moves)} files. Undo with: sloth.py {folder} --undo")


if __name__ == "__main__":
    main()
