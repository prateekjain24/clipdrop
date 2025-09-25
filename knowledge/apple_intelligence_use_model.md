# Apple Intelligence Use Model in Shortcuts (macOS 26)

## Prerequisites
- macOS 26 "Tahoe" on an Apple silicon Mac (M1 or later) with Apple Intelligence enabled in **System Settings ▸ Apple Intelligence & Siri**. Join the waitlist if the toggle is unavailable so the Use Model action appears in Shortcuts once Apple approves your device.
- Shortcuts 26 with access to the Apple Intelligence category in the Gallery—you can inspect Apple’s sample shortcuts to understand how they wire prompts, dictionary outputs, and follow-up flows.

## Build a Use Model action
1. **Create a new shortcut** and gather input first (`Get Contents of Clipboard`, `Get File`, `Get Text` as needed).
2. **Add “Use Model.”** Pick the provider each run should use: `On-Device` for offline runs, `Private Cloud Compute` for heavier jobs where latency is acceptable, or `Extension Model ▸ ChatGPT` if you must call OpenAI directly.
3. **Author the prompt**. Combine instructions and Shortcuts variables. For example:
   ```text
   Summarize the provided meeting transcript for ClipDrop engineers.
   Return {"title", "summary", "action_items", "open_questions"} as JSON.
   Prefer “Insufficient context” instead of guessing.
   ```
4. **Enable Follow Up** when you need interactive refinement; macOS will pause after the first response so you can add more context before continuing.
5. **Set a structured output.** Under *Output*, choose **Dictionary** and define keys (`title`, `summary`, etc.) so downstream actions (`Get Dictionary Value`, `Save File`) avoid brittle string parsing.
6. **Chain post-processing** steps: e.g., `Encode Dictionary` → `Run Shell Script` for schema validation or `Create Note` to persist Markdown.

## Testing & guardrails
- Wrap the Use Model call in an `If Apple Intelligence Is Available` branch. Fall back to a non-AI helper (heuristics or raw text) when the feature is off or the Mac lacks Apple silicon.
- Log the provider used (`On-Device` vs `PCC`) in the CLI output so teammates understand where data flowed. Shortcuts exposes this metadata after the Use Model action completes.
- Validate JSON output by piping to your CLI schema validator (see `shortcuts_cli.md`). This catches hallucinated keys before you hand the data to downstream services.

## Resources
- [Use Apple Intelligence in Shortcuts on Mac – Apple Support](https://support.apple.com/sq-al/guide/mac-help/mchl91750563/mac)
- [Here’s What You Can Do With the iOS 26 Apple Intelligence Shortcuts App – MacRumors](https://www.macrumors.com/2025/06/11/ios-26-shortcuts-app/)
- [Shortcuts app has chatbot-like Apple Intelligence powers in iOS 26 – 9to5Mac](https://9to5mac.com/2025/06/16/shortcuts-app-has-chatbot-like-apple-intelligence-powers-in-ios-26/)
