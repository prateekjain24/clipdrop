# Spotlight Actions & Quick Keys (macOS 26 Tahoe)

## Why it matters
Spotlight in macOS 26 adds Quick Keys, clipboard history, and action panes so ClipDrop shortcuts are one keystroke away from the system search field. You can launch automations, run App Intents, and complete common tasks without leaving Spotlight.

## Setup checklist
1. **Ship an App Intent** (see `app_intents_updates.md`) that wraps the CLI entry point, e.g., `SummarizeClipboardIntent`.
2. **Assign phrases and quick keys**. In Spotlight (`⌘ + Space`), press `⌘3` to focus the Actions pane, then click **Add Quick Key** next to your intent—use short mnemonics like `sc` for “summarize clipboard.”
3. **Test natural-language triggers** by typing “summarize clipboard detailed” or the quick key (`sc`) and confirm Spotlight previews the intent with parameters.
4. **Combine with clipboard history** (`⌘4`) to paste the most recent capture directly into your shortcut without opening an app.
5. **Teach the team**: Quick Keys sync via iCloud, so teammates on macOS 26 can adopt the same mnemonics for consistency.

## Automation tip for junior devs
Pair Spotlight invocation with folder automations. A folder-watcher shortcut can ingest new screenshots automatically, while Spotlight Quick Keys give you manual overrides when you need bespoke summaries.

## Resources
- [Take actions and shortcuts in Spotlight on Mac – Apple Support](https://support.apple.com/guide/mac-help/take-actions-and-shortcuts-in-spotlight-mchl4953dfeb/mac)
- [macOS 26: Spotlight gets actions, clipboard manager, and custom quick keys – 9to5Mac](https://9to5mac.com/2025/06/10/macos-26-spotlight-gets-actions-clipboard-manager-custom-shortcuts/)
- [Apple supercharges Spotlight in macOS Tahoe with Quick Keys – MacRumors](https://www.macrumors.com/2025/06/09/apple-supercharges-spotlight-in-macos-tahoe-with-quick-keys-and-more/)
- [Hands-on with macOS Tahoe 26 Spotlight – The Verge](https://www.theverge.com/apple/685052/apple-macos-tahoe-26-beta-hands-on-liquid-glass-themes-spotlight)
