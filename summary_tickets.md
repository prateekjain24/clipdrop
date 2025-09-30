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

#### Chunked Summarization Protocol (v1)
- **Trigger:** Python CLI switches to chunked mode when `len(content) > 15000` or when heuristic score indicates hierarchical summarization is required.
- **Invocation:** `summarize_content_with_chunking` pipes a UTF-8 JSON document to `clipdrop-summarize` via stdin and expects a single-line JSON response on stdout. Exit code `0` indicates the helper ran; response `success` determines logical outcome.

##### Request Payload
```json
{
  "version": "1.0",
  "mode": "chunked",
  "content_format": "markdown|plaintext|html",
  "origin": "clipdrop-cli",
  "instructions": "optional override for LLM directives",
  "chunks": [
    {
      "id": "uuid",
      "index": 0,
      "text": "...",
      "char_length": 7800,
      "token_estimate": 2600,
      "metadata": {
        "source_filename": "research.md",
        "section_title": "Findings"
      }
    }
  ],
  "strategy": {
    "type": "hierarchical",
    "max_chunk_chars": 12000,
    "target_summary_sentences": 4,
    "language": "en-US"
  }
}
```
- `chunks` are ordered; helper may assume incremental context. `id` is opaque but stable for retries.
- `token_estimate` allows Swift helper to choose batching; Python provides coarse `len(chunk) / 3` by default.
- `strategy.language` mirrors CLI `--lang`; omitted entries default to English.

##### Response Payload
```json
{
  "version": "1.0",
  "mode": "chunked",
  "success": true,
  "summary": "Consolidated 3-paragraph recap...",
  "stage_results": [
    {"stage": "precheck", "status": "ok"},
    {"stage": "chunk_summaries", "status": "ok", "processed": 4},
    {"stage": "aggregation", "status": "ok"}
  ],
  "elapsed_ms": 18342,
  "warnings": []
}
```
- `summary` is omitted when `success` is `false`; `error` and `retryable` fields become mandatory in that case.
- `stage_results` items follow enum set `{precheck, chunk_summaries, aggregation, refinement}` with optional `progress` (0–100).
- Helper should surface structured errors using:
  ```json
  {
    "success": false,
    "error": "Language model unavailable",
    "retryable": false,
    "stage": "precheck"
  }
  ```

##### CLI Contract
- Python interprets non-zero helper exit codes as transport failure and maps to `SummarizationResult(error=...)`.
- On chunk-level retries, Python may resend a subset of `chunks` with the same `version` but different `strategy.retry_attempt` counter; Swift should treat unknown fields as noop.
- Progress UI updates come from Python estimating completion based on chunk count; future streaming hooks can piggy-back on `stage_results` but are not required for v1.

##### Validation Rules
- Reject input when `chunks` is empty, any `text` exceeds `max_chunk_chars`, or `token_estimate` is missing.
- Return `retryable=true` for transient issues (e.g., `modelNotReady`, `timeout`); otherwise false.
- Preserve backward compatibility by continuing to accept legacy single-string input when `mode` is absent.

This spec lives inline for now; revise `version` when fields are added or behavior changes.

### T10 — Python chunking scaffolding
- **Goal:** Add chunk creation helpers (`create_semantic_chunks`, etc.) and `summarize_content_with_chunking` wrapper that emits protocol v1 payloads.
- **Details:** Build dataclasses for chunk metadata, JSON serializer aligned with `Chunked Summarization Protocol (v1)`, `strategy` heuristics, and retry bookkeeping; ensure fallback to single-pass helper remains.
- **Acceptance:** Unit tests cover chunk splitting, payload JSON, and error mapping; `summarize_content_with_chunking` routes long inputs through new codepath (Swift calls mocked).

### T11 — Swift chunked processing
- **Goal:** Extend `clipdrop-summarize` to accept protocol v1 JSON, summarize per chunk, consolidate, and emit structured status responses.
- **Acceptance:** Swift helper handles legacy single-string and new chunked inputs, populates `stage_results` / `warnings`, and ships fat binary via build scripts.

### T12 — CLI progress UX for chunking
- **Goal:** Enhance CLI progress display for multi-stage summarization, including stage messages sourced from Python chunk progress and helper `stage_results`.
- **Acceptance:** Running `--summarize` on long input shows multi-stage progress, stage-aligned status text, and final summary append.

### T13 — Integration tests for chunking flow
- **Goal:** Cover end-to-end workflow with mocked Swift responses implementing protocol v1 to ensure chunked summarization behaves correctly.
- **Acceptance:** New tests execute chunking path, verifying summary consolidation, error propagation (including `retryable`), and stage reporting.

### T14 — Documentation updates for chunking
- **Goal:** Document chunked summarization behavior, limits, protocol versioning expectations, and user guidance in README/help text.
- **Acceptance:** README/CLI help mention multi-stage strategy, platform requirements, and highlight fallback to single-pass summarization.
