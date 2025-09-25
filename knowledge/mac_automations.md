# macOS 26 Shortcuts Automations

## Supported triggers
Shortcuts on macOS 26 Tahoe now mirrors iOS automation triggers, including:
- **Folder events**: run a shortcut when files arrive in a watcher folder (ideal for Screenshots Inbox → summary).
- **External device**: trigger when you connect a specific display, microphone, or storage device.
- **Scheduled time**: daily or weekly summaries without user interaction.
- **Power state**: detect when the lid closes or power adapter changes to run cleanup routines.

## Create a folder automation
1. Open Shortcuts and switch to the **Automations** tab.
2. Click **New Automation ▸ Folder**.
3. Pick the inbox folder (e.g., `~/Downloads/Screenshots`).
4. Add actions:
   - `Get Contents of Folder → Filter for Images`
   - `Repeat with Each → Use Model` (from `apple_intelligence_use_model.md`)
   - `Save File` to `~/Library/Shortcuts/Outputs/digest`.
5. Toggle **Run Immediately** so the automation executes without confirmation.

## Device trigger example
```text
When: External Display is Connected (Studio Display)
Do:
  1. Run Shortcut "Summarize Meeting Notes"
  2. Run Shell Script: clipdrop summarize --mode actions --input ~/Documents/CurrentMeetingNotes.md
  3. Show Result in Notification Center
```
Use this to auto-summarize meeting docs whenever you dock at your desk.

## Testing tips for junior devs
- Run automations manually first (`Automations ▸ ⋯ ▸ Run`) to confirm the Use Model action has permission to access files.
- Keep watcher folders small; move processed files to an archive to prevent loops.
- Combine with the CLI validator to ensure schema compliance before sending notifications.

## Resources
- [Apple’s Shortcuts app is getting a huge upgrade in iOS 26 and macOS 26 – Tom’s Guide](https://www.tomsguide.com/computing/software/apples-shortcuts-app-is-getting-a-huge-upgrade-in-ios-26-and-macos-26-heres-how-it-will-help-you)
- [Use Apple Intelligence in Shortcuts on Mac – Apple Support](https://support.apple.com/sq-al/guide/mac-help/mchl91750563/mac)
