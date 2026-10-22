# 🦥 Sloth Sorter

Point it at a messy folder. It reads each file, decides where it belongs, gives it a clean name, and files it away. You do nothing.

Runs fully offline on an open-weight model through [Ollama](https://ollama.com). Pure Python standard library, no dependencies.

## Run it

```bash
ollama pull llama3.2:3b
python sloth.py ~/Downloads             # dry run: shows the plan
python sloth.py ~/Downloads --apply     # does it
python sloth.py ~/Downloads --undo      # changed your mind
```

Options: `--model <any ollama model>`, `--no-rename`, `--min-age <minutes>`.

## Why it's safe to be lazy

- **Dry run by default.** Nothing moves until you say `--apply`.
- **Fully undoable.** Every move is logged to `.sloth-undo.json`.
- **Never overwrites.** Name collisions get a numeric suffix.
- **Skips fresh files**, so nothing mid-download gets touched.
- **Degrades gracefully.** If the model is offline, it sorts by file extension.

## Why open matters here

- **Privacy:** your Downloads folder holds tax forms, IDs and receipts. File names and previews never leave your machine.
- **Offline and free:** no API key, no per-file cost, works on a plane.
- **Swappable:** change `--model` to try Qwen, Gemma or Mistral, or edit `CATEGORIES` and the system prompt to fit your own filing style. A closed API gives you neither the privacy nor that control.
