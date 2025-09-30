# ClipDrop Summarization – Story-Point Tickets

Each ticket is sized at 1 story point and can land independently. Suggested execution order is top-to-bottom, but tasks may run in parallel once their prerequisites are met.

## T1 – Scaffold SwiftPM target
- **Goal:** Create `swift/ClipdropSummarize` SwiftPM package that builds the `clipdrop-summarize` executable and mirrors the existing transcription helper layout.
- **Details:** Add `Package.swift`, source directory, and placeholder `main.swift` wiring; update build/ignore rules as needed.
- **Acceptance:** `swift build -c release` produces `clipdrop-summarize` binary; repository layout matches plan.

## T2 – Implement summarizer main
- **Goal:** Flesh out `main.swift` with availability checks, prompt/session wiring, and JSON output per doc sample.
- **Details:** Ensure `SystemLanguageModel` availability handling, context-length guard, `GenerationOptions` with explicit `sampling: nil`, and `SummaryResult` JSON-safe payloads.
- **Acceptance:** Running helper with mock stdin returns well-formed JSON; error cases surface structured failures.

## T3 – Package helper binary
- **Goal:** Integrate the new executable into the existing build pipeline and artifact layout.
- **Details:** Extend `scripts/build_swift.sh` (or equivalent) to build universal binaries and deposit into `clipdrop/bin`.
- **Acceptance:** Build script emits arm64/x86_64 fat binary at the expected path; CI/docs updated if necessary.

## T4 – Python bridge
- **Goal:** Implement `summarize_content` in `src/clipdrop/macos_ai.py`, plus `get_swift_helper_path` lookup mirroring transcription helper.
- **Details:** Add length guards, subprocess invocation, JSON parsing, timeout handling, and typed `SummaryResult` dataclass.
- **Acceptance:** Unit tests (or manual run) confirm success/error paths; missing helper yields friendly failure.

## T5 – Content suitability checks
- **Goal:** Add `is_summarizable_content` helper (or extend existing detection) to gate unsupported formats/sizes.
- **Details:** Reuse word-count, code sniffing, and format filters from plan; expose reason string for CLI messaging.
- **Acceptance:** Tests cover accept/reject cases across markdown, code, CSV, oversize, and short snippets.

## T6 – CLI flag integration
- **Goal:** Wire `--summarize` / `-S` Typer option into `main.py`, including progress UI and append workflow.
- **Details:** Ensure base content write succeeds before append, call suitability check, invoke summarizer, and append markdown summary.
- **Acceptance:** `clipdrop <file> --summarize` appends `## Summary` section when helper succeeds; skips gracefully otherwise; no regression in `--scan/-s`.

## T7 – Tests and fixtures
- **Goal:** Cover new logic with automated tests and sample payloads.
- **Details:** Add unit tests for Python helper (mocking subprocess), detection rules, and CLI flow (via Typer runner). Include sample JSON fixtures as needed.
- **Acceptance:** `pytest -q` passes locally; CI green.

## T8 – Documentation & release notes
- **Goal:** Update CLI help, README, and changelog to advertise summarization feature.
- **Details:** Document platform requirements, fallback behavior, and usage examples; mention new build step if applicable.
- **Acceptance:** Docs render correctly; version notes prepared for eventual release.

## Future – Advanced Summarization (Chunking)

### T9 — Define chunking protocol
- **Goal:** Specify JSON schema & CLI contract for chunked summarization across Python↔Swift.
- **Acceptance:** Shared doc (or inline spec) describing request/response format, stages, and errors.

### T10 — Python chunking scaffolding
- **Goal:** Add chunk creation helpers (`create_semantic_chunks`, etc.) and skeleton `summarize_content_with_chunking` wrapper.
- **Acceptance:** Helpers unit-tested; long inputs route through new codepath (stubbed Swift calls).

### T11 — Swift chunked processing
- **Goal:** Extend `clipdrop-summarize` to accept JSON input, summarize per chunk, consolidate, and emit structured status.
- **Acceptance:** Swift helper handles both single-string and chunked JSON inputs; builds pass.

### T12 — CLI progress UX for chunking
- **Goal:** Enhance CLI progress display for multi-stage summarization, including stage messages and percent updates.
- **Acceptance:** Running `--summarize` on long input shows multi-stage progress and final summary append.

### T13 — Integration tests for chunking flow
- **Goal:** Cover end-to-end workflow with mocked Swift responses to ensure chunked summarization behaves correctly.
- **Acceptance:** New tests execute chunking path, verifying summary consolidation and error handling.

### T14 — Documentation updates for chunking
- **Goal:** Document chunked summarization behavior, limits, and user guidance in README/help text.
- **Acceptance:** README/CLI help mention multi-stage strategy and platform requirements.
