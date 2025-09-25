# ClipDrop Shortcuts Exports (macOS 26)

Run `scripts/export_shortcuts.sh` on a Mac running macOS 26 with the latest Shortcuts app:

```bash
# export to shortcuts/ with version suffix v1 (default)
./scripts/export_shortcuts.sh

# override destination directory and version tag
VERSION=v2 ./scripts/export_shortcuts.sh artifacts/shortcuts
```

The exporter expects these shortcut names:
- ClipDrop Summarize Clipboard
- ClipDrop Actions Decisions
- ClipDrop Delta Summarizer
- ClipDrop Daily Digest

If you see “This build of the Shortcuts CLI does not expose the `shortcuts export` subcommand” update to the macOS 26 tooling, or export manually from the Shortcuts UI (**Right-click ▸ Share ▸ Export File…**) and drop the `.shortcut` bundles into this directory.

When the command succeeds you’ll get files like `shortcuts/clipdrop-summarize-clipboard-v1.shortcut`. Commit them so teammates can install the exact graph referenced in `knowledge/` docs.

> Tip: If the export fails with “Couldn’t communicate with a helper application,” open the Shortcuts app once, rerun the script, and approve the automation prompt for Terminal.
