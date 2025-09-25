# App Intents for ClipDrop (macOS 26)

## Goals for junior devs
- Wrap CLI entry points (for example `clipdrop summarize --mode tldr`) in native App Intents so Spotlight, Siri, and widgets can invoke them without opening Terminal.
- Use Xcode 16’s App Intents template to scaffold metadata, phrases, and Spotlight discoverability with minimal boilerplate.

## Quick start
1. **Create an App Intents extension** in Xcode (`File ▸ New ▸ Target ▸ App Intents Extension`). Keep it in Swift so you can iterate quickly alongside the CLI.
2. **Define the intent**:
   ```swift
   import AppIntents
   import Foundation

   struct SummarizeClipboardIntent: AppIntent {
       static var title: LocalizedStringResource = "Summarize Clipboard"
       static var description = IntentDescription(
           "Runs the ClipDrop shortcut that summarizes the current clipboard contents."
       )

       @Parameter(title: "Mode")
       var mode: SummaryMode

       static var parameterSummary: some ParameterSummary {
           Summary("Summarize clipboard in \(\.$mode)")
       }

       func perform() async throws -> some IntentResult {
           let payload = try JSONEncoder().encode(["mode": mode.rawValue])
           try await Process.run(
               URL(fileURLWithPath: "/usr/bin/env"),
               arguments: [
                   "shortcuts", "run", "ClipDrop Summarize",
                   "--ask", String(decoding: payload, as: UTF8.self)
               ]
           )
           return .result()
       }
   }

   enum SummaryMode: String, AppEnum {
       case tldr, actions, delta, digest

       static var typeDisplayRepresentation = TypeDisplayRepresentation(name: "Summary Mode")
       static var caseDisplayRepresentations: [SummaryMode: DisplayRepresentation] = [
           .tldr: "TL;DR",
           .actions: "Actions",
           .delta: "Delta",
           .digest: "Daily Digest"
       ]
   }
   ```
3. **Publish phrases** via `AppShortcutsProvider` so Spotlight knows how to surface the intent:
   ```swift
   struct ClipDropShortcuts: AppShortcutsProvider {
       static var appShortcuts: [AppShortcut] {
           AppShortcut(
               intent: SummarizeClipboardIntent(),
               phrases: [
                   "summarize clipboard",
                   "clipdrop summary",
                   "summarize clipboard in \(.parameter(\.$mode))"
               ],
               shortTitle: "Summarize",
               systemImageName: "note.text"
           )
       }
   }
   ```
4. **Test discoverability** on macOS 26. Build & run the extension, open Spotlight (`⌘ + Space`), and type “summarize clipboard detailed” to confirm the intent shows with your icon and summary.
5. **Ship with the app**. Embed the extension in the ClipDrop app bundle and enable the `AppIntents` capability so macOS registers the action everywhere (Spotlight, Siri, widgets).

## Tips
- Use the new App Intents asset generator in Xcode 16 to localize titles/descriptions early; junior devs can edit strings without touching code.
- Visual Intelligence APIs (part of Apple Intelligence) can enrich future intents that classify screenshots or audio before summarization.
- Keep the CLI arguments synchronized with the Python entry point; drift is the most common integration bug during onboarding.

## Resources
- [App Intents – Apple Developer Documentation](https://developer.apple.com/documentation/appintents)
- [Xcode 16 Release Notes – Apple Developer](https://developer.apple.com/documentation/xcode-release-notes/xcode-16-release-notes)
- [WWDC24 App Intents Highlights – Superwall Blog](https://www.superwall.com/blog/xcode-16-apple-intelligence)
