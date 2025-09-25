# Shortcuts Command-Line Interface (macOS 26)

## Core workflow
```bash
# Run a shortcut by name with clipboard input piped from pbpaste
pbpaste \
  | shortcuts run "ClipDrop Summarize Clipboard" \
      --input - \
      --output ~/Library/Shortcuts/Outputs/tldr.json
```
- `shortcuts run "ClipDrop Summarize Clipboard"` executes a saved shortcut exactly as if you tapped it in the Shortcuts app. The first run prompts for permission in Shortcuts; macOS remembers the approval afterwards.
- `--input -` streams stdin into the shortcut’s initial action (e.g., “Get Contents of Input”). Use `--ask` to answer prompts, or pass a file path if the shortcut expects documents.
- `--output` writes the final result to disk, handy for logging JSON dictionaries produced by the Use Model action.

## Bridge from Python (ClipDrop CLI)
```python
import subprocess
import json
from pathlib import Path

def summarize_clipboard(mode: str = "tldr") -> dict:
    output_path = Path("~/Library/Shortcuts/Outputs/summary.json").expanduser()
    cmd = [
        "shortcuts", "run", "ClipDrop Summarize",
        "--input", "-",
        "--output", str(output_path),
        "--ask", json.dumps({"mode": mode})
    ]
    # Use pbpaste to feed the clipboard contents.
    proc = subprocess.run(
        ["bash", "-lc", "pbpaste | " + " ".join(cmd)],
        capture_output=True, text=True, check=True
    )
    return json.loads(output_path.read_text())
```
- Always prefer `check=True` to fail fast when the shortcut encounters an error. Capture `proc.stderr` and surface it to the CLI user.
- On Intel Macs (or when Apple Intelligence is disabled), catch `CalledProcessError` and fall back to the heuristic summarizer path described in the Use Model notes.

## Helpful inspection commands
```bash
shortcuts list                     # enumerate installed shortcuts
shortcuts view "ClipDrop Summarize" # quick console preview of actions
shortcuts sign clipdrop_shortcuts   # notarize before sharing with the team
shortcuts export "ClipDrop Summarize" ~/clipdrop/shortcuts
```
- `shortcuts view` is perfect for junior devs who want to sanity-check that Use Model actions are configured as expected before running the CLI.
- Export `.shortcut` bundles into version control so reviewers can diff changes alongside the Python glue code.

## Resources
- [Run shortcuts from the command line – Apple Support](https://support.apple.com/guide/shortcuts-mac/run-shortcuts-from-the-command-line-apd455c82f02/mac)
- [Use Apple Intelligence in Shortcuts on Mac – Apple Support](https://support.apple.com/sq-al/guide/mac-help/mchl91750563/mac)
